"""
Independent import worker process
Runs separately from the main API to avoid blocking
"""
import time
import requests
import json
import uuid as uuid_lib
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv
from models import ImportJob, Database as DatabaseModel, Table as TableModel, Field as FieldModel

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

BACKEND_URL = 'http://localhost:8000'

def process_import_job(job_id: str, db: Session):
    """Process a single import job"""
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            print(f"Job {job_id} not found")
            return

        print(f"Processing job {job_id}")

        # Parse config if it's a string
        if isinstance(job.config, str):
            config = json.loads(job.config)
        else:
            config = job.config

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
            try:
                print(f"Processing table: {table_name}")

                # Get schema
                schema_response = requests.post(
                    f"{BACKEND_URL}/api/database/schema",
                    json={**config, 'tableName': table_name},
                    timeout=30
                )
                schema_response.raise_for_status()
                schema_data = schema_response.json()

                # Get descriptions
                desc_response = requests.post(
                    f"{BACKEND_URL}/api/database/describe",
                    json={'tableName': table_name, 'fields': schema_data.get('fields', [])},
                    timeout=30
                )
                desc_response.raise_for_status()
                desc_data = desc_response.json()

                # Create table
                new_table = TableModel(
                    id=uuid_lib.uuid4(),
                    database_id=created_db_id,
                    name=table_name,
                    description=schema_data.get('table_description', f'Stores {table_name} data')
                )
                db.add(new_table)
                db.flush()

                # Bulk create fields
                fields_to_add = []
                for field in desc_data.get('fields', []):
                    new_field = FieldModel(
                        id=uuid_lib.uuid4(),
                        table_id=new_table.id,
                        name=field['fieldName'],
                        type=field['dataType'],
                        description=field.get('description', ''),
                        nullable=field.get('isNullable') == 'YES',
                        is_primary_key=field.get('isPrimaryKey') == 'YES',
                        is_foreign_key=field.get('isForeignKey') == 'YES',
                        default_value=field.get('defaultValue')
                    )
                    fields_to_add.append(new_field)

                db.bulk_save_objects(fields_to_add)
                db.commit()

                imported_count += 1
                print(f"Imported table {table_name} ({imported_count}/{len(selected_tables)})")

                # Update progress every 5 tables
                if imported_count % 5 == 0:
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

        # Final update
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
        print(f"Error processing job {job_id}: {e}")
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            db.commit()

def main():
    """Main worker loop - polls for pending jobs"""
    print("Import worker started")

    while True:
        db = SessionLocal()
        try:
            # Find pending jobs
            pending_jobs = db.query(ImportJob).filter(
                ImportJob.status == 'pending'
            ).order_by(ImportJob.created_at).all()

            if pending_jobs:
                for job in pending_jobs:
                    # Mark as in progress
                    job.status = 'in_progress'
                    job.updated_at = datetime.utcnow()
                    db.commit()

                    # Process the job
                    process_import_job(str(job.id), db)

            db.close()

            # Wait before checking again
            time.sleep(2)

        except Exception as e:
            print(f"Worker error: {e}")
            db.close()
            time.sleep(5)

if __name__ == "__main__":
    main()
