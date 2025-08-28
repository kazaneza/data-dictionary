from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, UUID4
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uvicorn
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, Text, func, Integer, NVARCHAR, delete
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import os
from dotenv import load_dotenv
import logging
import sys
import uuid
import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from config import ADMIN_USERS, MANAGER_USERS, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
from routers.database_import import router as database_import_router
from routers import search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add the database import router
app.include_router(
    database_import_router,
    prefix="/api/database",
    tags=["database-import"]
)

# Add the search router
app.include_router(
    search.router,
    prefix="/api",
    tags=["search"]
)
# SQL Server connection settings
SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
USERNAME = os.getenv("DB_USERNAME")
PASSWORD = os.getenv("DB_PASSWORD")

if not all([SERVER, DATABASE, USERNAME, PASSWORD]):
    logger.error("Missing database configuration. Please check your .env file")
    raise ValueError("Missing database configuration")

# Create connection string for SQL Server
try:
    CONNECTION_STRING = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes"
    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={CONNECTION_STRING}",
        pool_pre_ping=True,
        pool_recycle=3600
    )
    logger.info("Database connection established successfully")
except Exception as e:
    logger.error(f"Failed to create database connection: {str(e)}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define Database Models
class SourceSystem(Base):
    __tablename__ = "source_systems"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name = Column(NVARCHAR(255), nullable=False)
    description = Column(NVARCHAR(1000))
    category = Column(NVARCHAR(100))

class Database(Base):
    __tablename__ = "databases"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    source_id = Column(UNIQUEIDENTIFIER, ForeignKey("source_systems.id"))
    name = Column(NVARCHAR(255), nullable=False)
    description = Column(NVARCHAR(1000))
    type = Column(NVARCHAR(50))
    platform = Column(NVARCHAR(50))
    location = Column(NVARCHAR(255))
    version = Column(NVARCHAR(50))

class Table(Base):
    __tablename__ = "tables"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    database_id = Column(UNIQUEIDENTIFIER, ForeignKey("databases.id"))
    category_id = Column(UNIQUEIDENTIFIER, ForeignKey("categories.id"))
    name = Column(NVARCHAR(255), nullable=False)
    description = Column(NVARCHAR(1000))

class Field(Base):
    __tablename__ = "fields"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    table_id = Column(UNIQUEIDENTIFIER, ForeignKey("tables.id"))
    name = Column(NVARCHAR(255), nullable=False)
    type = Column(NVARCHAR(50), nullable=False)
    description = Column(NVARCHAR(1000))
    nullable = Column(Boolean, default=True)
    is_primary_key = Column(Boolean, default=False)
    is_foreign_key = Column(Boolean, default=False)
    default_value = Column(NVARCHAR(255))

class Category(Base):
    __tablename__ = "categories"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name = Column(NVARCHAR(255), nullable=False)
    description = Column(NVARCHAR(1000))

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Auth models
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    token: str
    role: str

def get_user_role(username: str) -> str:
    """Determine user role based on username"""
    if username in ADMIN_USERS:
        return "admin"
    elif username in MANAGER_USERS:
        return "manager"
    return "user"

# Auth endpoint
@app.post("/auth/login", response_model=Token)
async def login(request: LoginRequest):
    try:
        # In a real application, you would verify the password against a secure store
        # For this example, we're using a simple check
        if not request.password:  # Basic validation
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        # Get user role
        role = get_user_role(request.username)
        
        # Create JWT token
        token_data = {
            "sub": request.username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        }
        token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return {"token": token, "role": role}
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

# Security dependency
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"username": username, "role": role}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Dependency for Database Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Routes
@app.get("/dashboard/stats")
def get_dashboard_stats(user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        logger.debug("Fetching dashboard statistics")
        stats = {
            "total_sources": db.query(func.count(SourceSystem.id)).scalar() or 0,
            "total_tables": db.query(func.count(Table.id)).scalar() or 0,
            "total_fields": db.query(func.count(Field.id)).scalar() or 0,
            "active_systems": db.query(func.count(Database.id)).scalar() or 0
        }
        logger.info(f"Dashboard statistics retrieved successfully: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error retrieving dashboard statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Source Systems CRUD
@app.get("/sources")
def get_sources(user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        sources = db.query(SourceSystem).all()
        logger.info(f"Retrieved {len(sources)} source systems")
        return sources
    except Exception as e:
        logger.error(f"Error retrieving sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sources")
def create_source(source: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to create sources")
    
    try:
        db_source = SourceSystem(**source)
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        logger.info(f"Created new source system: {db_source.name}")
        return db_source
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/sources/{source_id}")
def update_source(source_id: UUID4, source: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to update sources")
    
    try:
        db_source = db.query(SourceSystem).filter(SourceSystem.id == source_id).first()
        if not db_source:
            raise HTTPException(status_code=404, detail="Source system not found")
        
        for key, value in source.items():
            setattr(db_source, key, value)
        
        db.commit()
        db.refresh(db_source)
        logger.info(f"Updated source system: {db_source.name}")
        return db_source
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sources/{source_id}")
def delete_source(source_id: UUID4, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete sources")
    
    try:
        # Get the source system
        db_source = db.query(SourceSystem).filter(SourceSystem.id == source_id).first()
        if not db_source:
            raise HTTPException(status_code=404, detail="Source system not found")

        # Get all databases for this source
        databases = db.query(Database).filter(Database.source_id == source_id).all()
        
        # For each database, get its tables and delete their fields
        for database in databases:
            # Get all tables for this database
            tables = db.query(Table).filter(Table.database_id == database.id).all()
            
            # For each table, delete its fields
            for table in tables:
                # Delete fields
                db.query(Field).filter(Field.table_id == table.id).delete()
            
            # Delete tables
            db.query(Table).filter(Table.database_id == database.id).delete()
        
        # Delete databases
        db.query(Database).filter(Database.source_id == source_id).delete()
        
        # Finally, delete the source system
        db.query(SourceSystem).filter(SourceSystem.id == source_id).delete()
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Deleted source system: {db_source.name}")
        return {"message": "Source system and all related items deleted successfully"}
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Databases CRUD
@app.get("/databases")
def get_databases(user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        databases = db.query(Database).all()
        logger.info(f"Retrieved {len(databases)} databases")
        return databases
    except Exception as e:
        logger.error(f"Error retrieving databases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/databases")
def create_database(database: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to create databases")
    
    try:
        db_database = Database(**database)
        db.add(db_database)
        db.commit()
        db.refresh(db_database)
        logger.info(f"Created new database: {db_database.name}")
        return db_database
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/databases/{database_id}")
def update_database(database_id: UUID4, database: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to update databases")
    
    try:
        db_database = db.query(Database).filter(Database.id == database_id).first()
        if not db_database:
            raise HTTPException(status_code=404, detail="Database not found")
        
        for key, value in database.items():
            setattr(db_database, key, value)
        
        db.commit()
        db.refresh(db_database)
        logger.info(f"Updated database: {db_database.name}")
        return db_database
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/databases/{database_id}")
def delete_database(database_id: UUID4, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete databases")
    
    try:
        # Get the database first to check if it exists
        db_database = db.query(Database).filter(Database.id == database_id).first()
        if not db_database:
            raise HTTPException(status_code=404, detail="Database not found")

        # Get all tables for this database
        tables = db.query(Table).filter(Table.database_id == database_id).all()
        
        # For each table, delete its fields
        for table in tables:
            # Delete fields
            db.query(Field).filter(Field.table_id == table.id).delete()
        
        # Delete tables
        db.query(Table).filter(Table.database_id == database_id).delete()
        
        # Delete the database
        db.query(Database).filter(Database.id == database_id).delete()
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Deleted database: {db_database.name}")
        return {"message": "Database and all related items deleted successfully"}
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Tables CRUD
@app.get("/tables")
def get_tables(user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tables = db.query(Table).all()
        logger.info(f"Retrieved {len(tables)} tables")
        return tables
    except Exception as e:
        logger.error(f"Error retrieving tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tables")
def create_table(table: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to create tables")
    
    try:
        db_table = Table(**table)
        db.add(db_table)
        db.commit()
        db.refresh(db_table)
        logger.info(f"Created new table: {db_table.name}")
        return db_table
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/tables/{table_id}")
def update_table(table_id: UUID4, table: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to update tables")
    
    try:
        db_table = db.query(Table).filter(Table.id == table_id).first()
        if not db_table:
            raise HTTPException(status_code=404, detail="Table not found")
        
        for key, value in table.items():
            setattr(db_table, key, value)
        
        db.commit()
        db.refresh(db_table)
        logger.info(f"Updated table: {db_table.name}")
        return db_table
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tables/{table_id}")
def delete_table(table_id: UUID4, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete tables")
    
    try:
        # Get the table first to check if it exists
        db_table = db.query(Table).filter(Table.id == table_id).first()
        if not db_table:
            raise HTTPException(status_code=404, detail="Table not found")

        # Delete all fields for this table
        db.query(Field).filter(Field.table_id == table_id).delete()
        
        # Delete the table
        db.query(Table).filter(Table.id == table_id).delete()
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Deleted table: {db_table.name}")
        return {"message": "Table and all related fields deleted successfully"}
    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Fields CRUD
@app.get("/fields")
def get_fields(table_id: str = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        if table_id:
            fields = db.query(Field).filter(Field.table_id == table_id).all()
        else:
            fields = db.query(Field).all()
        logger.info(f"Retrieved {len(fields)} fields")
        return fields
    except Exception as e:
        logger.error(f"Error retrieving fields: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fields")
def create_field(field: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to create fields")
    
    try:
        db_field = Field(**field)
        db.add(db_field)
        db.commit()
        db.refresh(db_field)
        logger.info(f"Created new field: {db_field.name}")
        return db_field
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating field: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/fields/{field_id}")
def update_field(field_id: UUID4, field: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to update fields")
    
    try:
        db_field = db.query(Field).filter(Field.id == field_id).first()
        if not db_field:
            raise HTTPException(status_code=404, detail="Field not found")
        
        for key, value in field.items():
            setattr(db_field, key, value)
        
        db.commit()
        db.refresh(db_field)
        logger.info(f"Updated field: {db_field.name}")
        return db_field
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating field: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/fields/{field_id}")
def delete_field(field_id: UUID4, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete fields")
    
    try:
        db_field = db.query(Field).filter(Field.id == field_id).first()
        if not db_field:
            raise HTTPException(status_code=404, detail="Field not found")
        
        db.delete(db_field)
        db.commit()
        logger.info(f"Deleted field: {db_field.name}")
        return {"message": "Field deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting field: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Categories CRUD
@app.get("/categories")
def get_categories(user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        categories = db.query(Category).all()
        logger.info(f"Retrieved {len(categories)} categories")
        return categories
    except Exception as e:
        logger.error(f"Error retrieving categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/categories")
def create_category(category: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to create categories")
    
    try:
        db_category = Category(**category)
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        logger.info(f"Created new category: {db_category.name}")
        return db_category
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/categories/{category_id}")
def update_category(category_id: UUID4, category: dict, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update categories")
    
    try:
        db_category = db.query(Category).filter(Category.id == category_id).first()
        if not db_category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        for key, value in category.items():
            setattr(db_category, key, value)
        
        db.commit()
        db.refresh(db_category)
        logger.info(f"Updated category: {db_category.name}")
        return db_category
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/categories/{category_id}")
def delete_category(category_id: UUID4, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete categories")
    
    try:
        db_category = db.query(Category).filter(Category.id == category_id).first()
        if not db_category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        db.delete(db_category)
        db.commit()
        logger.info(f"Deleted category: {db_category.name}")
        return {"message": "Category deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)