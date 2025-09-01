"""
Database import router with clean separation of concerns
"""

from fastapi import APIRouter, HTTPException
import logging

from .models import DatabaseConfig, SchemaRequest, DescribeFieldsRequest, TableField
from .ai_descriptions import AIDescriptionGenerator
from ..database_connections import get_connection_handler

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/connect")
async def connect_database(config: DatabaseConfig):
    """Connect to database and retrieve table list"""
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
        logger.error(error_msg, exc_info=True)
        
        # Provide more specific error details for Oracle connections
        if config.type == "Oracle" and "service" in str(e).lower():
            detailed_error = {
                "message": "Oracle connection failed",
                "error": str(e),
                "type": config.type,
                "suggestions": [
                    f"Verify the service name '{config.database}' is correct",
                    "Try using SID instead of service name",
                    "Check if the Oracle listener is running on the target server",
                    "Verify the server address and port (default: 1521)"
                ]
            }
        else:
            detailed_error = {
                "message": "Failed to connect to database",
                "error": str(e),
                "type": config.type
            }
        
        raise HTTPException(
            status_code=500,
            detail=detailed_error
        )

@router.post("/schema")
async def get_schema(request: SchemaRequest):
    """Get table schema with AI-generated descriptions"""
    try:
        logger.info(f"Getting schema for table {request.tableName}")
        
        # Get source system information for context
        from database import SessionLocal
        from models import SourceSystem
        
        db = SessionLocal()
        try:
            source_system = db.query(SourceSystem).filter(SourceSystem.id == request.source_id).first()
            source_name = source_system.name if source_system else "Unknown System"
            source_description = source_system.description if source_system else None
        finally:
            db.close()
        
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
            
            # Generate table description using AI
            table_description = AIDescriptionGenerator.generate_table_description(
                request.tableName, table_fields, source_name, source_description
            )
            
            # Generate field descriptions using AI
            table_fields = AIDescriptionGenerator.generate_field_descriptions(
                request.tableName, table_fields, source_name, source_description
            )
            
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
async def describe_fields(request: DescribeFieldsRequest):
    """Generate descriptions for existing fields"""
    try:
        table_name = request.tableName
        fields = [TableField(**field) for field in request.fields]
        source_name = request.source_name or "Unknown System"
        source_description = request.source_description
        
        if not table_name or not fields:
            raise HTTPException(
                status_code=400,
                detail="Table name and fields are required"
            )

        # Generate descriptions for fields using AI
        fields_with_descriptions = AIDescriptionGenerator.generate_field_descriptions(
            table_name, fields, source_name, source_description
        )
        
        return {"fields": [field.dict() for field in fields_with_descriptions]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to describe fields: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to describe fields", "error": str(e)}
        )