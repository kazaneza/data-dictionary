from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
from .database_connections import get_connection_handler

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

router = APIRouter()

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

def generate_table_description(table_name: str, fields: List[TableField]) -> str:
    """Generate a description for a table using OpenAI."""
    try:
        # Create a prompt that includes table name and field information
        field_info = "\n".join([
            f"- {field.fieldName} ({field.dataType}): " +
            f"{'Primary Key, ' if field.isPrimaryKey == 'Yes' else ''}" +
            f"{'Foreign Key, ' if field.isForeignKey == 'Yes' else ''}" +
            f"{'Nullable, ' if field.isNullable == 'Yes' else 'Required, '}" +
            f"Default: {field.defaultValue if field.defaultValue else 'None'}"
            for field in fields
        ])

        prompt = f"""Given a database table named '{table_name}' with the following fields:

{field_info}

Generate a clear, concise description of this table's purpose and the type of data it stores. 
Focus on business context and relationships. Keep the description under 200 characters."""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a database expert helping to document table structures."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )

        description = response.choices[0].message.content.strip()
        logger.info(f"Generated description for table {table_name}: {description}")
        return description

    except Exception as e:
        logger.error(f"Error generating table description: {str(e)}")
        return f"Table containing {table_name} related data"

def generate_field_descriptions(table_name: str, fields: List[TableField]) -> List[TableField]:
    """Generate descriptions for fields using OpenAI."""
    try:
        # Create a prompt that includes context about all fields
        fields_context = "\n".join([
            f"- {field.fieldName} ({field.dataType}): " +
            f"{'Primary Key, ' if field.isPrimaryKey == 'Yes' else ''}" +
            f"{'Foreign Key, ' if field.isForeignKey == 'Yes' else ''}" +
            f"{'Nullable, ' if field.isNullable == 'Yes' else 'Required, '}" +
            f"Default: {field.defaultValue if field.defaultValue else 'None'}"
            for field in fields
        ])

        prompt = f"""For the table '{table_name}' with these fields:

{fields_context}

Generate a clear, concise description (max 100 characters) for each field, explaining its purpose and business context."""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a database expert helping to document field meanings."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        # Parse the response and update field descriptions
        descriptions = response.choices[0].message.content.strip().split("\n")
        for field, description in zip(fields, descriptions):
            # Clean up the description
            clean_desc = re.sub(r'^[^:]*:', '', description).strip()
            field.description = clean_desc

        logger.info(f"Generated descriptions for {len(fields)} fields in table {table_name}")
        return fields

    except Exception as e:
        logger.error(f"Error generating field descriptions: {str(e)}")
        return fields

@router.post("/connect")
async def connect_database(config: DatabaseConfig):
    try:
        logger.info(f"Attempting to connect to {config.type} database at {config.server}")
        logger.debug(f"Connection details: server={config.server}, database={config.database}, username={config.username}")
        
        # Get the appropriate connection handler
        connection_class = get_connection_handler(config.type)
        handler = connection_class(config.dict())

        with handler:
            tables = handler.get_tables()
            logger.info(f"Successfully retrieved {len(tables)} tables from {config.type} database")
            return {"tables": tables}

    except ValueError as ve:
        logger.error(f"Invalid database type: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Include full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to connect to database",
                "error": str(e),
                "type": config.type
            }
        )

@router.post("/schema")
async def get_schema(request: SchemaRequest):
    try:
        logger.info(f"Getting schema for table {request.tableName}")
        # Get the appropriate connection handler
        connection_class = get_connection_handler(request.type)
        handler = connection_class(request.dict())

        with handler:
            # Get table schema
            fields = handler.get_table_schema(request.tableName)
            logger.debug(f"Retrieved {len(fields)} fields for table {request.tableName}")
            
            # Convert to TableField objects
            table_fields = [TableField(
                tableName=request.tableName,
                fieldName=field["fieldName"],
                dataType=field["dataType"],
                isNullable=field["isNullable"],
                isPrimaryKey=field["isPrimaryKey"],
                isForeignKey=field["isForeignKey"],
                defaultValue=field["defaultValue"]
            ) for field in fields]
            
            # Generate table description
            table_description = generate_table_description(request.tableName, table_fields)
            
            # Generate field descriptions
            table_fields = generate_field_descriptions(request.tableName, table_fields)
            
            logger.info(f"Successfully processed schema for table {request.tableName}")
            return {
                "fields": [field.dict() for field in table_fields],
                "table_description": table_description
            }

    except ValueError as ve:
        logger.error(f"Schema retrieval failed with ValueError: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to fetch schema: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to fetch schema", "error": str(e)}
        )

@router.post("/describe")
async def describe_fields(request: dict):
    try:
        table_name = request.get("tableName")
        fields = [TableField(**field) for field in request.get("fields", [])]
        
        if not table_name or not fields:
            raise HTTPException(
                status_code=400,
                detail="Table name and fields are required"
            )

        # Generate descriptions for fields
        fields_with_descriptions = generate_field_descriptions(table_name, fields)
        
        return {"fields": [field.dict() for field in fields_with_descriptions]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to describe fields: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to describe fields", "error": str(e)}
        )