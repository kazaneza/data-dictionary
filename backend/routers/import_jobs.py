from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime, timedelta
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

        # Parse existing config if it's a string, then merge with new data
        if isinstance(job.config, str):
            existing_config = json.loads(job.config)
        else:
            existing_config = job.config if job.config else {}

        # Store config with selected tables for worker (as JSON string)
        config_data = {**existing_config, **config, 'selected_tables': json.dumps(selected_tables)}
        job.config = json.dumps(config_data)
        job.status = 'pending'
        job.updated_at = datetime.utcnow()
        db.commit()

        return {"success": True, "message": "Import job queued for processing"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/import-jobs/diagnostics/worker-status")
def get_worker_diagnostics(db: Session = Depends(get_db)):
    """Check if the import worker is likely running by checking for stale pending jobs"""
    try:
        # Get all pending and in_progress jobs
        pending_jobs = db.query(ImportJob).filter(
            ImportJob.status.in_(['pending', 'in_progress'])
        ).order_by(ImportJob.created_at.desc()).all()
        
        # Check for jobs that haven't been updated in a while (likely worker not running)
        now = datetime.utcnow()
        stale_threshold = timedelta(hours=2)
        stale_jobs = []
        recent_jobs = []
        
        for job in pending_jobs:
            time_since_update = now - (job.updated_at if job.updated_at else job.created_at)
            if time_since_update > stale_threshold:
                stale_jobs.append({
                    "id": str(job.id),
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    "hours_since_update": round(time_since_update.total_seconds() / 3600, 2)
                })
            else:
                recent_jobs.append({
                    "id": str(job.id),
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                })
        
        # Determine worker status
        worker_likely_running = len(stale_jobs) == 0 and len(recent_jobs) > 0
        worker_status = "unknown"
        recommendations = []
        
        if len(stale_jobs) > 0:
            worker_status = "likely_not_running"
            recommendations.append("The import worker process may not be running. Check if 'python backend/import_worker.py' is running.")
            recommendations.append(f"Found {len(stale_jobs)} job(s) that haven't been updated in over 2 hours.")
        elif len(recent_jobs) > 0:
            worker_status = "likely_running"
            recommendations.append("Worker appears to be processing jobs.")
        else:
            worker_status = "no_jobs"
            recommendations.append("No pending jobs found. Worker status cannot be determined.")
        
        return {
            "worker_status": worker_status,
            "stale_jobs_count": len(stale_jobs),
            "recent_jobs_count": len(recent_jobs),
            "stale_jobs": stale_jobs[:5],  # Limit to 5 most recent
            "recent_jobs": recent_jobs[:5],
            "recommendations": recommendations,
            "check_timestamp": now.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background processing is now handled by the separate import_worker.py process
