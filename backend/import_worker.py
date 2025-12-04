"""
Independent import worker process
Runs separately from the main API to avoid blocking
"""
import time
import requests
import json
import uuid as uuid_lib
import signal
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from models import ImportJob, Database as DatabaseModel, Table as TableModel, Field as FieldModel, SourceSystem
from routers.database_import.ai_descriptions import AIDescriptionGenerator
from routers.database_import.models import TableField

# Global flag for graceful shutdown
shutdown_requested = False

load_dotenv()

SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
USERNAME = os.getenv("DB_USERNAME")
PASSWORD = os.getenv("DB_PASSWORD")

CONNECTION_STRING = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes"
engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={CONNECTION_STRING}",
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dynamic BACKEND_URL configuration
# Priority: 1. Environment variable, 2. Default to localhost
def get_backend_url():
    backend_url = os.getenv("BACKEND_URL") or os.getenv("VITE_API_URL")
    if backend_url:
        return backend_url.rstrip('/')  # Remove trailing slash if present
    # Default to localhost for local development
    return 'http://localhost:8000'

BACKEND_URL = get_backend_url()
print(f"Worker using BACKEND_URL: {BACKEND_URL}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    print("\nShutdown signal received. Finishing current job and exiting...")
    shutdown_requested = True

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

def check_job_cancelled(job_id: str, db: Session) -> bool:
    """Check if a job has been cancelled"""
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if job and job.status == 'cancelled':
        return True
    return False

def process_import_job(job_id: str, db: Session):
    """Process a single import job"""
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            print(f"Job {job_id} not found")
            return

        print(f"Processing job {job_id}")
        print(f"Config type: {type(job.config)}")
        print(f"Config value: {job.config}")

        # Parse config if it's a string
        if isinstance(job.config, str):
            config = json.loads(job.config)
        else:
            config = job.config

        print(f"Parsed config type: {type(config)}")
        print(f"Parsed config: {config}")

        selected_tables = json.loads(config.get('selected_tables', '[]'))

        imported_count = 0
        failed_tables = []
        created_db_id = None

        # Create database entry
        try:
            new_db = DatabaseModel(
                id=uuid_lib.uuid4(),
                source_id=config.get('source_id'),
                name=config.get('database'),
                description=config.get('description'),
                type=config.get('type'),
                platform=config.get('platform'),
                location=config.get('location'),
                version=config.get('version')
            )
            db.add(new_db)
            db.commit()
            db.refresh(new_db)
            created_db_id = new_db.id
            print(f"Created database {created_db_id}")
        except Exception as e:
            print(f"Failed to create database: {e}")
            job.status = 'failed'
            job.error_message = f'Failed to create database: {str(e)}'
            job.updated_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        # Process each table
        for table_name in selected_tables:
            # Check if job was cancelled or shutdown requested
            if shutdown_requested:
                print(f"Shutdown requested. Stopping job {job_id}")
                job.status = 'cancelled'
                job.error_message = 'Worker shutdown requested'
                job.updated_at = datetime.utcnow()
                job.completed_at = datetime.utcnow()
                db.commit()
                return
            
            # Check if job was cancelled from frontend
            if check_job_cancelled(job_id, db):
                print(f"Job {job_id} was cancelled. Stopping processing.")
                job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
                if job:
                    job.status = 'cancelled'
                    job.error_message = 'Job cancelled by user'
                    job.updated_at = datetime.utcnow()
                    job.completed_at = datetime.utcnow()
                    db.commit()
                return
            
            try:
                print(f"Processing table: {table_name}")

                # Get schema (fast, no AI) - exclude selected_tables from config spread
                config_for_api = {k: v for k, v in config.items() if k != 'selected_tables'}
                try:
                    schema_response = requests.post(
                        f"{BACKEND_URL}/api/database/schema",
                        json={**config_for_api, 'tableName': table_name},
                        timeout=60  # Should be fast now without AI
                    )
                    schema_response.raise_for_status()
                    schema_data = schema_response.json()
                except requests.exceptions.RequestException as e:
                    print(f"Failed to connect to backend API at {BACKEND_URL}: {e}")
                    raise Exception(f"Backend API unavailable: {str(e)}")

                # Get source system info for AI context
                source_system = db.query(SourceSystem).filter(SourceSystem.id == config.get('source_id')).first()
                source_name = source_system.name if source_system else "Unknown System"
                source_description = source_system.description if source_system else None

                # Convert fields to TableField objects
                table_fields = [TableField(
                    tableName=table_name,
                    fieldName=field['fieldName'],
                    dataType=field['dataType'],
                    isNullable=field['isNullable'],
                    isPrimaryKey=field['isPrimaryKey'],
                    isForeignKey=field['isForeignKey'],
                    defaultValue=field['defaultValue']
                ) for field in schema_data.get('fields', [])]

                # Generate AI descriptions in worker (background)
                print(f"Generating AI descriptions for {len(table_fields)} fields...")
                table_description = AIDescriptionGenerator.generate_table_description(
                    table_name, table_fields, source_name, source_description
                )
                table_fields = AIDescriptionGenerator.generate_field_descriptions(
                    table_name, table_fields, source_name, source_description
                )
                print(f"AI descriptions generated")

                # Get table record count
                print(f"Counting records in {table_name}...")
                from routers.database_connections import get_connection_handler
                connection_class = get_connection_handler(config.get('type'))
                handler = connection_class(config_for_api)
                with handler:
                    record_count = handler.get_table_count(table_name)
                print(f"Table {table_name} has {record_count} records")

                # Create table with stats
                new_table = TableModel(
                    id=uuid_lib.uuid4(),
                    database_id=created_db_id,
                    name=table_name,
                    description=table_description,
                    record_count=record_count,
                    last_imported=datetime.now()
                )
                db.add(new_table)
                db.flush()

                # Bulk create fields
                fields_to_add = []
                for field in table_fields:
                    new_field = FieldModel(
                        id=uuid_lib.uuid4(),
                        table_id=new_table.id,
                        name=field.fieldName,
                        type=field.dataType,
                        description=field.description or '',
                        nullable=field.isNullable == 'YES',
                        is_primary_key=field.isPrimaryKey == 'YES',
                        is_foreign_key=field.isForeignKey == 'YES',
                        default_value=field.defaultValue
                    )
                    fields_to_add.append(new_field)

                db.bulk_save_objects(fields_to_add)
                db.commit()

                imported_count += 1
                print(f"Imported table {table_name} ({imported_count}/{len(selected_tables)})")

                # Update progress after each table (for better UX)
                # Refresh job to get latest status
                db.refresh(job)
                if job.status == 'cancelled':
                    print(f"Job {job_id} was cancelled during processing. Stopping.")
                    return
                
                job.imported_tables = imported_count
                job.updated_at = datetime.utcnow()
                db.commit()

            except Exception as e:
                print(f"Failed to import table {table_name}: {e}")
                db.rollback()
                failed_tables.append(table_name)
                job.failed_tables = json.dumps(failed_tables)
                job.updated_at = datetime.utcnow()
                db.commit()

        # Final update - check if job was cancelled before finalizing
        db.refresh(job)
        if job.status == 'cancelled':
            print(f"Job {job_id} was cancelled. Finalizing cancellation.")
            job.error_message = f'Job cancelled. {imported_count} tables were imported before cancellation.'
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        job.imported_tables = imported_count
        job.updated_at = datetime.utcnow()
        final_status = 'completed' if failed_tables == [] else ('failed' if imported_count == 0 else 'completed')
        job.status = final_status
        job.failed_tables = json.dumps(failed_tables)
        job.database_id = created_db_id
        job.error_message = f'{len(failed_tables)} tables failed' if failed_tables else None
        job.completed_at = datetime.utcnow()
        db.commit()

        print(f"Job {job_id} completed: {imported_count} tables imported")

    except Exception as e:
        import traceback
        print(f"Error processing job {job_id}: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            db.commit()

def main():
    """Main worker loop - polls for pending jobs"""
    global shutdown_requested
    print("Import worker started")
    print("Press Ctrl+C to stop gracefully (will finish current job)")

    while not shutdown_requested:
        db = SessionLocal()
        try:
            # Find pending jobs (also check for in_progress jobs that might need resuming)
            # Exclude cancelled, completed, and failed jobs
            pending_jobs = db.query(ImportJob).filter(
                ImportJob.status.in_(['pending', 'in_progress'])
            ).filter(
                ImportJob.status != 'cancelled'
            ).order_by(ImportJob.created_at).all()

            if pending_jobs:
                for job in pending_jobs:
                    # Check if shutdown was requested
                    if shutdown_requested:
                        break
                    
                    # Skip if already cancelled
                    if job.status == 'cancelled':
                        continue
                    
                    # Mark as in progress if it was pending
                    if job.status == 'pending':
                        job.status = 'in_progress'
                        job.updated_at = datetime.utcnow()
                        db.commit()

                    # Process the job
                    process_import_job(str(job.id), db)
                    
                    # Break if shutdown requested after processing
                    if shutdown_requested:
                        break

            db.close()

            # Wait before checking again (unless shutdown requested)
            if not shutdown_requested:
                time.sleep(2)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt received. Shutting down gracefully...")
            shutdown_requested = True
            db.close()
            break
        except Exception as e:
            print(f"Worker error: {e}")
            db.close()
            if not shutdown_requested:
                time.sleep(5)
    
    print("Worker stopped gracefully.")

if __name__ == "__main__":
    main()
