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

def get_source_system_context(source_name: str) -> str:
    """Get context about the source system to help OpenAI provide better descriptions."""
    source_lower = source_name.lower()
    
    # Banking systems
    if any(keyword in source_lower for keyword in ['t24', 'core banking', 'banking', 'temenos']):
        return "This is a core banking system (T24/Temenos). Focus on banking operations like accounts, transactions, customers, loans, deposits, and financial processing."
    
    # ERP systems
    elif any(keyword in source_lower for keyword in ['sap', 'oracle', 'erp', 'enterprise']):
        return "This is an Enterprise Resource Planning (ERP) system. Focus on business processes like finance, procurement, inventory, human resources, and operations management."
    
    # CRM systems
    elif any(keyword in source_lower for keyword in ['crm', 'customer', 'salesforce', 'dynamics']):
        return "This is a Customer Relationship Management (CRM) system. Focus on customer data, sales processes, marketing campaigns, and customer interactions."
    
    # HR systems
    elif any(keyword in source_lower for keyword in ['hr', 'human resource', 'payroll', 'employee']):
        return "This is a Human Resources system. Focus on employee data, payroll, benefits, performance management, and workforce analytics."
    
    # Financial systems
    elif any(keyword in source_lower for keyword in ['finance', 'accounting', 'ledger', 'financial']):
        return "This is a financial/accounting system. Focus on financial transactions, accounting entries, budgets, and financial reporting."
    
    # Default
    else:
        return f"This is a business system called '{source_name}'. Analyze the table and field names to understand the business domain and provide relevant descriptions."
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
                {"role": "system", "content": "You are a senior database analyst with expertise in various business systems including banking, financial services, ERP, CRM, and other enterprise applications. Analyze the table and field names to understand the business domain and provide clear, business-focused descriptions that help users understand the practical purpose of database tables and fields."},
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

def generate_table_description_with_context(table_name: str, fields: List[TableField], source_context: str) -> str:
    """Generate a description for a table using OpenAI with source system context."""
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

        prompt = f"""You are a database analyst. Provide a SHORT, clear description of what this table stores.

System Context: {source_context}

Table: {table_name}
Fields:

{field_info}

IMPORTANT: Write ONLY 1-2 short sentences (max 150 characters total) explaining:

1. What data this table stores
2. Its main business purpose

Keep it simple and direct. Example: "Stores customer account transactions and balances for daily banking operations."
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a database analyst. Write very short, clear descriptions. Maximum 150 characters. Be direct and simple."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,  # Much shorter responses
            temperature=0.1
        )

        description = response.choices[0].message.content.strip()
        
        # Ensure description doesn't exceed database limit (500 chars to be very safe)
        if len(description) > 500:
            description = description[:500].rsplit('.', 1)[0] + '.'
        
        logger.info(f"Generated context-aware description for table {table_name}: {description}")
        return description

    except Exception as e:
        logger.error(f"Error generating table description with context: {str(e)}")

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

def generate_field_descriptions_with_context(table_name: str, fields: List[TableField], source_context: str) -> List[TableField]:
    """Generate descriptions for fields using OpenAI with source system context."""
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

        prompt = f"""You are a senior database analyst and business systems expert. Analyze this table and provide comprehensive, business-focused descriptions for each field.

System Context: {source_context}

Table: {table_name}
Fields:

{fields_context}

CRITICAL REQUIREMENTS: For each field, provide a concise business description (1-2 sentences, max 150 words per field) that explains:

1. WHAT: What specific business data this field contains (be very detailed about the content)
2. WHY: Why this data is important for business operations
3. HOW: How this field is used in real business processes and workflows



Focus on business value and practical usage. Keep descriptions concise but informative.

Format your response as:
fieldName: description

Make each description concise and business-focused (1-2 sentences each, under 150 words)."""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior database analyst and business systems expert with 15+ years of experience across banking, ERP, CRM, and enterprise systems. You excel at creating concise, business-focused field descriptions that help stakeholders understand what data is stored, why it matters, and how it's used in business operations. Keep descriptions under 150 words per field."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,  # Reduced to ensure shorter descriptions
            temperature=0.2
        )

        # Parse the response and update field descriptions
        response_text = response.choices[0].message.content.strip()
        description_lines = [line.strip() for line in response_text.split('\n') if line.strip() and ':' in line]
        
        # Create a mapping of field names to descriptions
        field_descriptions = {}
        for line in description_lines:
            if ':' in line:
                field_name, description = line.split(':', 1)
                desc = description.strip()
                # Ensure field description doesn't exceed database limit (900 chars to be safe)
                if len(desc) > 900:
                    desc = desc[:900].rsplit('.', 1)[0] + '.'
                field_descriptions[field_name.strip()] = desc
        
        # Update field descriptions
        for field in fields:
            if field.fieldName in field_descriptions:
                field.description = field_descriptions[field.fieldName]
            else:
                # Fallback description if OpenAI didn't provide one
                # Generate a better fallback based on field name analysis
                field.description = generate_fallback_description(field.fieldName, field.dataType, table_name)

        logger.info(f"Generated context-aware descriptions for {len(fields)} fields in table {table_name}")
        return fields

    except Exception as e:
        logger.error(f"Error generating field descriptions with context: {str(e)}")
        return fields

def generate_fallback_description(field_name: str, data_type: str, table_name: str) -> str:
    """Generate a better fallback description when OpenAI fails."""
    field_lower = field_name.lower()
    
    # Common field patterns with better descriptions
    if 'id' in field_lower and ('customer' in field_lower or 'client' in field_lower):
        return f"Unique identifier linking to customer records, used for customer relationship tracking, data integrity, and cross-system references. This ID enables efficient lookups and maintains referential integrity across all customer-related business processes."
    elif 'id' in field_lower and field_lower.endswith('_id'):
        entity = field_name[:-3].replace('_', ' ').title()
        return f"Foreign key reference to {entity} records, establishing relational data integrity and enabling efficient joins. This identifier maintains business relationships and supports data consistency across the system's operational workflows."
    elif 'amount' in field_lower or 'balance' in field_lower:
        return f"Monetary value stored as {data_type}, representing financial amounts in the system's base currency. This field is critical for financial calculations, reporting, compliance, and audit trails, with precision maintained for accurate accounting."
    elif 'date' in field_lower or 'time' in field_lower:
        return f"Timestamp field ({data_type}) recording when specific business events occurred, essential for audit trails, compliance reporting, and business analytics. This temporal data supports regulatory requirements and operational tracking."
    elif 'status' in field_lower or 'state' in field_lower:
        return f"Status indicator controlling business logic and workflow states for {table_name.replace('_', ' ').lower()} records. This field drives automated processes, user permissions, and business rule execution throughout the system."
    elif 'code' in field_lower:
        return f"Standardized code value ({data_type}) used for categorization, business rule processing, and system integration. These codes ensure data consistency and enable efficient processing across different business functions."
    elif 'name' in field_lower or 'description' in field_lower:
        return f"Descriptive text field ({data_type}) providing human-readable information for business users, reports, and customer communications. This field enhances data usability and supports clear business documentation."
    elif 'account' in field_lower:
        return f"Account reference ({data_type}) linking to financial account structures and transaction processing systems. This field enables account-based operations, balance tracking, and customer service functions."
    elif 'number' in field_lower:
        return f"Numeric identifier or sequence ({data_type}) used for unique identification, business referencing, and system integration. This number supports efficient data retrieval and maintains business process continuity."
    else:
        # Generic but better fallback
        clean_name = field_name.replace('_', ' ').title()

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
        
        # Get source system information for context
        from database import SessionLocal
        from models import SourceSystem
        
        db = SessionLocal()
        try:
            source_system = db.query(SourceSystem).filter(SourceSystem.id == request.source_id).first()
            source_context = get_source_system_context(source_system.name if source_system else "Unknown System")
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
            
            # Generate table description
            table_description = generate_table_description_with_context(request.tableName, table_fields, source_context)
            
            # Generate field descriptions
            table_fields = generate_field_descriptions_with_context(request.tableName, table_fields, source_context)
            
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