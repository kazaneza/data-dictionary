from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, Text, func, Integer, NVARCHAR
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import uuid

Base = declarative_base()

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
    description = Column(NVARCHAR(2000))  # Increased from 1000 to 2000 characters

class Field(Base):
    __tablename__ = "fields"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    table_id = Column(UNIQUEIDENTIFIER, ForeignKey("tables.id"))
    name = Column(NVARCHAR(255), nullable=False)
    type = Column(NVARCHAR(500), nullable=False)  # Increased from 50 to 500 to accommodate longer types
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