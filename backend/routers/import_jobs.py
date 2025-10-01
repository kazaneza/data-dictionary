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
    """Queue an import job for processing by the worker"""
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Import job not found")

        # Store config with selected tables for worker
        job.config = {**config, 'selected_tables': json.dumps(selected_tables)}
        job.status = 'pending'
        job.updated_at = datetime.utcnow()
        db.commit()

        return {"success": True, "message": "Import job queued for processing"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Background processing is now handled by the separate import_worker.py process
