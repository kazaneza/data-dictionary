from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime
import json
import uuid
from database import get_db
from models import ImportJob

router = APIRouter()

class ImportJobCreate(BaseModel):
    user_id: str
    config: dict
    total_tables: int

class ImportJobUpdate(BaseModel):
    status: Optional[str] = None
    imported_tables: Optional[int] = None
    failed_tables: Optional[List[str]] = None
    error_message: Optional[str] = None
    database_id: Optional[UUID4] = None
    completed_at: Optional[datetime] = None

@router.post("/import-jobs")
def create_import_job(job: ImportJobCreate, db: Session = Depends(get_db)):
    try:
        db_job = ImportJob(
            id=uuid.uuid4(),
            user_id=job.user_id,
            config=json.dumps(job.config),
            status='pending',
            total_tables=job.total_tables,
            imported_tables=0
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)

        return {
            "id": str(db_job.id),
            "user_id": db_job.user_id,
            "config": json.loads(db_job.config),
            "status": db_job.status,
            "total_tables": db_job.total_tables,
            "imported_tables": db_job.imported_tables,
            "failed_tables": json.loads(db_job.failed_tables) if db_job.failed_tables else [],
            "error_message": db_job.error_message,
            "database_id": str(db_job.database_id) if db_job.database_id else None,
            "created_at": db_job.created_at.isoformat() if db_job.created_at else None,
            "updated_at": db_job.updated_at.isoformat() if db_job.updated_at else None,
            "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import-jobs/{job_id}")
def get_import_job(job_id: UUID4, db: Session = Depends(get_db)):
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")

        return {
            "id": str(job.id),
            "user_id": job.user_id,
            "config": json.loads(job.config),
            "status": job.status,
            "total_tables": job.total_tables,
            "imported_tables": job.imported_tables,
            "failed_tables": json.loads(job.failed_tables) if job.failed_tables else [],
            "error_message": job.error_message,
            "database_id": str(job.database_id) if job.database_id else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import-jobs/user/{user_id}")
def get_user_import_jobs(user_id: str, status: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(ImportJob).filter(ImportJob.user_id == user_id)

        if status:
            statuses = status.split(',')
            query = query.filter(ImportJob.status.in_(statuses))

        jobs = query.order_by(ImportJob.created_at.desc()).all()

        return [{
            "id": str(job.id),
            "user_id": job.user_id,
            "config": json.loads(job.config),
            "status": job.status,
            "total_tables": job.total_tables,
            "imported_tables": job.imported_tables,
            "failed_tables": json.loads(job.failed_tables) if job.failed_tables else [],
            "error_message": job.error_message,
            "database_id": str(job.database_id) if job.database_id else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        } for job in jobs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/import-jobs/{job_id}")
def update_import_job(job_id: UUID4, update: ImportJobUpdate, db: Session = Depends(get_db)):
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")

        if update.status is not None:
            job.status = update.status
        if update.imported_tables is not None:
            job.imported_tables = update.imported_tables
        if update.failed_tables is not None:
            job.failed_tables = json.dumps(update.failed_tables)
        if update.error_message is not None:
            job.error_message = update.error_message
        if update.database_id is not None:
            job.database_id = update.database_id
        if update.completed_at is not None:
            job.completed_at = update.completed_at

        job.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(job)

        return {
            "id": str(job.id),
            "user_id": job.user_id,
            "config": json.loads(job.config),
            "status": job.status,
            "total_tables": job.total_tables,
            "imported_tables": job.imported_tables,
            "failed_tables": json.loads(job.failed_tables) if job.failed_tables else [],
            "error_message": job.error_message,
            "database_id": str(job.database_id) if job.database_id else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-jobs/{job_id}/process")
async def process_import_job(job_id: UUID4, config: dict, selected_tables: List[str], user_info: dict = None, db: Session = Depends(get_db)):
    """Start processing an import job in the background"""
    import threading

    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")

        job.status = 'in_progress'
        job.updated_at = datetime.utcnow()
        db.commit()

        thread = threading.Thread(
            target=process_import_job_background,
            args=(str(job_id), config, selected_tables, user_info)
        )
        thread.daemon = True
        thread.start()

        return {"success": True, "message": "Import job started"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def process_import_job_background(job_id: str, config: dict, selected_tables: List[str], user_info: dict = None):
    """Process import job in background thread"""
    import requests
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os
    from dotenv import load_dotenv
    import uuid as uuid_lib
    from models import ImportJob, Database as DatabaseModel, Table as TableModel, Field as FieldModel

    load_dotenv()

    SERVER = os.getenv("DB_SERVER")
    DATABASE = os.getenv("DB_NAME")
    USERNAME = os.getenv("DB_USERNAME")
    PASSWORD = os.getenv("DB_PASSWORD")

    CONNECTION_STRING = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes"
    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={CONNECTION_STRING}",
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            return

        backend_url = 'http://localhost:8000'
        imported_count = 0
        failed_tables = []
        created_db_id = None

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
        except Exception as e:
            job.status = 'failed'
            job.error_message = f'Failed to create database: {str(e)}'
            job.updated_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        for table_name in selected_tables:
            try:
                schema_response = requests.post(f"{backend_url}/api/database/schema", json={
                    **config,
                    'tableName': table_name
                }, timeout=10)
                schema_response.raise_for_status()
                schema_data = schema_response.json()

                desc_response = requests.post(f"{backend_url}/api/database/describe", json={
                    'tableName': table_name,
                    'fields': schema_data.get('fields', [])
                }, timeout=10)
                desc_response.raise_for_status()
                desc_data = desc_response.json()

                new_table = TableModel(
                    id=uuid_lib.uuid4(),
                    database_id=created_db_id,
                    name=table_name,
                    description=schema_data.get('table_description', f'Stores {table_name} data')
                )
                db.add(new_table)
                db.flush()

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

                if imported_count % 5 == 0:
                    job.imported_tables = imported_count
                    job.updated_at = datetime.utcnow()
                    db.commit()

            except Exception as e:
                db.rollback()
                failed_tables.append(table_name)
                job.failed_tables = json.dumps(failed_tables)
                job.updated_at = datetime.utcnow()
                db.commit()

        job.imported_tables = imported_count
        job.updated_at = datetime.utcnow()

        final_status = 'completed' if failed_tables == [] else ('failed' if imported_count == 0 else 'completed')
        job.status = final_status
        job.imported_tables = imported_count
        job.failed_tables = json.dumps(failed_tables)
        job.database_id = created_db_id
        job.error_message = f'{len(failed_tables)} tables failed' if failed_tables else None
        job.updated_at = datetime.utcnow()
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
