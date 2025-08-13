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

        prompt = f"""You are a database expert analyzing a banking/financial system table. 

Table: {table_name}
Fields:

{field_info}

Based on the table name and field structure, provide a detailed business description of what this table stores and its purpose in the system.

Consider:
- What business process or entity does this represent?
- What kind of transactions or data would be stored here?
- How might this table be used in business operations?
- What relationships might it have with other system components?

Provide a clear, informative description (2-3 sentences) that would help a business user understand the table's purpose."""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior database analyst with expertise in banking and financial systems. You understand T24 core banking, statement processing, account management, and financial data structures. Provide clear, business-focused descriptions that help users understand the practical purpose of database tables and fields."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )

        description = response.choices[0].message.content.strip()
        logger.info(f"Generated description for table {table_name}: {description}")
        return description

    except Exception as e:
        logger.error(f"Error generating table description: {str(e)}")
        return f"Database table for {table_name.replace('_', ' ').title()} data storage and management"

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

        prompt = f"""You are analyzing a banking/financial system table. Provide business-focused descriptions for each field.

Table: {table_name}
Fields:

{fields_context}

For each field, provide a clear business description that explains:
- What data this field contains
- How it's used in business processes
- Its relationship to banking/financial operations
- Any business rules or constraints

Format your response as:
fieldName: description

Keep descriptions informative but concise (1-2 sentences each)."""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior database analyst specializing in banking and financial systems. You understand T24 core banking, account structures, transaction processing, and financial data relationships. Provide practical, business-focused field descriptions that help users understand how each field is used in real banking operations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )

        # Parse the response and update field descriptions
        response_text = response.choices[0].message.content.strip()
        description_lines = [line.strip() for line in response_text.split('\n') if line.strip() and ':' in line]
        
        # Create a mapping of field names to descriptions
        field_descriptions = {}
        for line in description_lines:
            if ':' in line:
                field_name, description = line.split(':', 1)
                field_descriptions[field_name.strip()] = description.strip()
        
        # Update field descriptions
        for field in fields:
            if field.fieldName in field_descriptions:
                field.description = field_descriptions[field.fieldName]
            else:
                # Fallback description if OpenAI didn't provide one
                field.description = f"Data field for {field.fieldName.replace('_', ' ').lower()} information"

        logger.info(f"Generated descriptions for {len(fields)} fields in table {table_name}")
        return fields

    except Exception as e:
        logger.error(f"Error generating field descriptions: {str(e)}")

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