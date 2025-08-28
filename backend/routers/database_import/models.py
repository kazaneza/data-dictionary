"""
Pydantic models for database import functionality
"""

from pydantic import BaseModel
from typing import List, Optional

class DatabaseConfig(BaseModel):
    server: str
    database: str
    username: str
    password: str
    type: str
    source_id: str
    description: Optional[str] = None
    platform: Optional[str] = None
    location: Optional[str] = None
    version: Optional[str] = None

class TableField(BaseModel):
    tableName: str
    fieldName: str
    dataType: str
    isNullable: str
    isPrimaryKey: str
    isForeignKey: str
    defaultValue: Optional[str] = None
    description: Optional[str] = None

class SchemaRequest(DatabaseConfig):
    tableName: str

class DescribeFieldsRequest(BaseModel):
    tableName: str
    fields: List[dict]
    source_name: Optional[str] = None
    source_description: Optional[str] = None