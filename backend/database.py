from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()