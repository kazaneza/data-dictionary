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
def get_banking_context_prompt(source_name: str, source_description: str, table_name: str, fields: List[TableField]) -> str:
    """Generate enhanced banking-specific context for better descriptions"""
    
    # Banking system patterns and terminology
    banking_patterns = {
        'temenos': {
            'system_type': 'Temenos T24 Core Banking',
            'common_prefixes': {
                'AA': 'Arrangement Architecture (loans, deposits)',
                'AC': 'Account Management',
                'AM': 'Asset Management', 
                'CU': 'Customer Management',
                'FT': 'Funds Transfer',
                'MM': 'Money Market',
                'SC': 'Securities',
                'PD': 'Product Definition',
                'LD': 'Loans and Deposits',
                'DE': 'Deal Entry',
                'RE': 'Reporting',
                'ST': 'Standing Instructions',
                'TF': 'Trade Finance',
                'FX': 'Foreign Exchange'
            },
            'field_patterns': {
                'AMT': 'Amount (monetary value)',
                'LCY': 'Local Currency',
                'FCY': 'Foreign Currency', 
                'CCY': 'Currency Code',
                'BAL': 'Balance',
                'DR': 'Debit',
                'CR': 'Credit',
                'TXN': 'Transaction',
                'ACCT': 'Account',
                'CUST': 'Customer',
                'PROD': 'Product',
                'RATE': 'Interest Rate',
                'DATE': 'Date',
                'TIME': 'Time',
                'STATUS': 'Status/State',
                'CODE': 'Reference Code',
                'DESC': 'Description',
                'REF': 'Reference',
                'NO': 'Number/Sequence',
                'ID': 'Identifier',
                'TYPE': 'Type/Category',
                'LIMIT': 'Limit/Threshold',
                'CHARGE': 'Fee/Charge',
                'COMM': 'Commission'
            }
        },
        'core_banking': {
            'system_type': 'Core Banking System',
            'modules': ['accounts', 'loans', 'deposits', 'payments', 'cards', 'treasury']
        },
        'payment': {
            'system_type': 'Payment Processing System',
            'focus': 'transaction processing, settlement, clearing'
        },
        'risk': {
            'system_type': 'Risk Management System', 
            'focus': 'credit risk, market risk, operational risk'
        }
    }
    
    # Detect system type
    source_lower = source_name.lower()
    desc_lower = (source_description or '').lower()
    
    system_context = ""
    field_hints = {}
    
    if any(term in source_lower or term in desc_lower for term in ['temenos', 't24']):
        context = banking_patterns['temenos']
        system_context = f"This is a {context['system_type']} system."
        field_hints = context['field_patterns']
        
        # Add module-specific context based on table name
        table_prefix = table_name[:2].upper() if len(table_name) >= 2 else ''
        if table_prefix in context['common_prefixes']:
            system_context += f" This table is part of {context['common_prefixes'][table_prefix]} module."
    
    elif any(term in source_lower or term in desc_lower for term in ['core banking', 'banking', 'bank']):
        system_context = "This is a Core Banking System handling customer accounts, transactions, loans, and deposits."
    
    elif any(term in source_lower or term in desc_lower for term in ['payment', 'swift', 'ach', 'wire']):
        system_context = "This is a Payment Processing System handling money transfers, settlements, and clearing operations."
    
    return system_context, field_hints

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
    try:
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
"""  # <--- Add this line

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a database analyst. Write very short, clear descriptions. Maximum 150 characters. Be direct and simple."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.1
        )

        description = response.choices[0].message.content.strip()
        
        if len(description) > 500:
            description = description[:500].rsplit('.', 1)[0] + '.'
        
        logger.info(f"Generated context-aware description for table {table_name}: {description}")
        return description

    except Exception as e:
        logger.error(f"Error generating table description with context: {str(e)}")

def generate_enhanced_banking_table_description(table_name: str, fields: List[TableField], source_name: str, source_description: str) -> str:
    """Generate banking-specific table descriptions with domain knowledge"""
    try:
        system_context, field_hints = get_banking_context_prompt(source_name, source_description, table_name, fields)
        
        # Analyze field patterns for better context
        field_analysis = []
        for field in fields:
            field_upper = field.fieldName.upper()
            analysis = f"- {field.fieldName} ({field.dataType})"
            
            # Add banking-specific insights
            for pattern, meaning in field_hints.items():
                if pattern in field_upper:
                    analysis += f" [{meaning}]"
                    break
            
            if field.isPrimaryKey == 'Yes':
                analysis += " [Primary Key]"
            if field.isForeignKey == 'Yes':
                analysis += " [Foreign Key]"
                
            field_analysis.append(analysis)
        
        field_info = "\n".join(field_analysis)
        
        prompt = f"""You are a banking systems expert analyzing a data dictionary.

Source System: {source_name}
System Description: {source_description or 'Banking system'}
Context: {system_context}

Table: {table_name}
Fields Analysis:
{field_info}

Based on your banking domain expertise and the field patterns, provide a precise business description of what this table stores and its role in banking operations.

REQUIREMENTS:
- Maximum 120 characters
- Focus on business purpose, not technical details
- Use banking terminology appropriately
- Be specific about the type of banking data stored

Example: "Stores customer account balances and transaction limits for daily banking operations"
"""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior banking systems analyst with deep knowledge of core banking, payment systems, and financial data structures. Provide concise, accurate business descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.1
        )

        description = response.choices[0].message.content.strip()
        
        # Ensure length constraint
        if len(description) > 120:
            description = description[:120].rsplit(' ', 1)[0] + '...'
        
        logger.info(f"Generated enhanced banking description for table {table_name}: {description}")
        return description

    except Exception as e:
        logger.error(f"Error generating enhanced banking table description: {str(e)}")
        # Fallback to pattern-based description
        return generate_banking_fallback_table_description(table_name, fields, source_name)

def generate_banking_fallback_table_description(table_name: str, fields: List[TableField], source_name: str) -> str:
    """Generate fallback descriptions using banking patterns"""
    table_upper = table_name.upper()
    
    # Banking table patterns
    if any(term in table_upper for term in ['CUSTOMER', 'CLIENT', 'CU']):
        return "Stores customer information and relationship data for banking services"
    elif any(term in table_upper for term in ['ACCOUNT', 'AC', 'ACCT']):
        return "Manages bank account details, balances, and account-related information"
    elif any(term in table_upper for term in ['TRANSACTION', 'TXN', 'TRANS', 'FT']):
        return "Records financial transactions and money movement activities"
    elif any(term in table_upper for term in ['LOAN', 'CREDIT', 'LD']):
        return "Manages loan accounts, credit facilities, and lending operations"
    elif any(term in table_upper for term in ['DEPOSIT', 'SAVINGS', 'TD']):
        return "Handles deposit accounts and savings product information"
    elif any(term in table_upper for term in ['PAYMENT', 'PAY']):
        return "Processes payment instructions and settlement transactions"
    elif any(term in table_upper for term in ['RATE', 'INTEREST']):
        return "Stores interest rates and pricing information for banking products"
    elif any(term in table_upper for term in ['LIMIT', 'THRESHOLD']):
        return "Defines transaction limits and operational thresholds"
    elif any(term in table_upper for term in ['CHARGE', 'FEE', 'COMM']):
        return "Manages fees, charges, and commission structures"
    else:
        # Generic banking fallback
        source_lower = source_name.lower()
        if 'temenos' in source_lower or 't24' in source_lower:
            return f"Temenos T24 data table for {table_name.replace('_', ' ').lower()} management"
        else:
            return f"Banking system table for {table_name.replace('_', ' ').lower()} operations"

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

        prompt = f"""You are a database analyst. Provide SHORT descriptions for each field.

System Context: {source_context}

Table: {table_name}
Fields:

{fields_context}

IMPORTANT: Write ONLY 1 short sentence (max 80 characters) for each field explaining what data it stores.

Format your response as:
fieldName: description

Keep it simple and direct. Examples:
- customer_id: Customer unique identifier
- amount: Transaction amount in currency
- date_created: Record creation timestamp"""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a database analyst. Write very short, clear descriptions. Maximum 80 characters per field. Be direct and simple."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
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
                # Ensure field description doesn't exceed 80 characters
                if len(desc) > 80:
                    desc = desc[:80].strip()
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

def generate_enhanced_banking_field_descriptions(table_name: str, fields: List[TableField], source_name: str, source_description: str) -> List[TableField]:
    """Generate banking-specific field descriptions with domain intelligence"""
    try:
        system_context, field_hints = get_banking_context_prompt(source_name, source_description, table_name, fields)
        
        # Build enhanced field context
        fields_context = []
        for field in fields:
            field_upper = field.fieldName.upper()
            context_line = f"- {field.fieldName} ({field.dataType})"
            
            # Add banking pattern hints
            hints = []
            for pattern, meaning in field_hints.items():
                if pattern in field_upper:
                    hints.append(meaning)
            
            if field.isPrimaryKey == 'Yes':
                hints.append("Primary Key")
            if field.isForeignKey == 'Yes':
                hints.append("Foreign Key")
            if field.isNullable == 'NO':
                hints.append("Required")
            if field.defaultValue:
                hints.append(f"Default: {field.defaultValue}")
                
            if hints:
                context_line += f" [{', '.join(hints)}]"
                
            fields_context.append(context_line)

        prompt = f"""You are a banking systems expert creating field descriptions for a data dictionary.

Source System: {source_name}
System Description: {source_description or 'Banking system'}
Context: {system_context}

Table: {table_name}
Fields:
{chr(10).join(fields_context)}

For each field, provide a precise business description focusing on:
- What banking data it stores
- Its business purpose in banking operations
- Banking-specific terminology where appropriate

REQUIREMENTS:
- Maximum 60 characters per description
- Use banking domain knowledge
- Be specific and business-focused
- Format: fieldName: description

Examples:
- CUSTOMER_ID: Unique customer identifier for account linking
- BALANCE_AMT: Current account balance in local currency
- TXN_DATE: Transaction processing date and time
"""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior banking systems analyst. Create precise, business-focused field descriptions using banking terminology."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.2
        )

        # Parse response and update field descriptions
        response_text = response.choices[0].message.content.strip()
        description_lines = [line.strip() for line in response_text.split('\n') if line.strip() and ':' in line]
        
        field_descriptions = {}
        for line in description_lines:
            if ':' in line:
                field_name, description = line.split(':', 1)
                desc = description.strip()
                # Ensure field description doesn't exceed 60 characters
                if len(desc) > 60:
                    desc = desc[:60].strip()
                field_descriptions[field_name.strip()] = desc
        
        # Update field descriptions with banking-aware fallbacks
        for field in fields:
            if field.fieldName in field_descriptions:
                field.description = field_descriptions[field.fieldName]
            else:
                field.description = generate_banking_fallback_field_description(field.fieldName, field.dataType, table_name, source_name)

        logger.info(f"Generated enhanced banking descriptions for {len(fields)} fields in table {table_name}")
        return fields

    except Exception as e:
        logger.error(f"Error generating enhanced banking field descriptions: {str(e)}")
        # Fallback to banking pattern-based descriptions
        for field in fields:
            field.description = generate_banking_fallback_field_description(field.fieldName, field.dataType, table_name, source_name)
        return fields

def generate_banking_fallback_field_description(field_name: str, data_type: str, table_name: str, source_name: str) -> str:
    """Generate banking-specific fallback descriptions"""
    field_upper = field_name.upper()
    
    # Banking field patterns with specific meanings
    banking_patterns = {
        'CUSTOMER_ID': 'Unique customer identifier for account linking',
        'ACCOUNT_ID': 'Unique account identifier for transactions',
        'ACCOUNT_NO': 'Customer-facing account number',
        'BALANCE': 'Current account balance amount',
        'AVAILABLE_BAL': 'Available balance for transactions',
        'LEDGER_BAL': 'Ledger balance including pending items',
        'AMT': 'Monetary amount in specified currency',
        'AMOUNT': 'Transaction or balance amount',
        'CCY': 'ISO currency code (USD, EUR, etc.)',
        'CURRENCY': 'Currency denomination for amounts',
        'LCY_AMT': 'Amount converted to local currency',
        'FCY_AMT': 'Amount in foreign currency',
        'TXN_DATE': 'Transaction processing date',
        'VALUE_DATE': 'Value date for interest calculation',
        'MATURITY_DATE': 'Product maturity or expiry date',
        'RATE': 'Interest rate or exchange rate',
        'INTEREST_RATE': 'Annual interest rate percentage',
        'CHARGE_AMT': 'Fee or charge amount applied',
        'COMMISSION': 'Commission amount or percentage',
        'STATUS': 'Current status or state of record',
        'PRODUCT_CODE': 'Banking product identifier',
        'BRANCH_CODE': 'Bank branch identifier',
        'GL_CODE': 'General ledger account code',
        'REFERENCE': 'Transaction or system reference',
        'DESCRIPTION': 'Descriptive text or narrative',
        'LIMIT_AMT': 'Credit or transaction limit amount',
        'OVERDRAFT': 'Overdraft facility amount',
        'TENOR': 'Loan or deposit term period',
        'FREQUENCY': 'Payment or interest frequency'
    }
    
    # Check for exact matches first
    if field_upper in banking_patterns:
        return banking_patterns[field_upper]
    
    # Pattern matching for partial matches
    if 'CUSTOMER' in field_upper and 'ID' in field_upper:
        return 'Customer unique identifier'
    elif 'ACCOUNT' in field_upper and 'ID' in field_upper:
        return 'Account unique identifier'
    elif 'BALANCE' in field_upper or 'BAL' in field_upper:
        return 'Account balance amount'
    elif 'AMOUNT' in field_upper or 'AMT' in field_upper:
        return 'Monetary amount value'
    elif 'DATE' in field_upper:
        return 'Date field for banking operations'
    elif 'TIME' in field_upper:
        return 'Timestamp for transaction processing'
    elif 'RATE' in field_upper:
        return 'Rate value for calculations'
    elif 'CODE' in field_upper:
        return 'Reference code for categorization'
    elif 'STATUS' in field_upper or 'STATE' in field_upper:
        return 'Status indicator for record state'
    elif 'LIMIT' in field_upper:
        return 'Limit or threshold amount'
    elif 'CHARGE' in field_upper or 'FEE' in field_upper:
        return 'Fee or charge amount'
    elif 'CURRENCY' in field_upper or 'CCY' in field_upper:
        return 'Currency code or denomination'
    elif 'DESCRIPTION' in field_upper or 'DESC' in field_upper:
        return 'Descriptive text information'
    elif 'NUMBER' in field_upper or 'NO' in field_upper:
        return 'Numeric identifier or sequence'
    elif 'NAME' in field_upper:
        return 'Name or title information'
    elif 'TYPE' in field_upper:
        return 'Type or category classification'
    else:
        # Generic banking fallback
        clean_name = field_name.replace('_', ' ').title()
        return f"{clean_name} banking data field"

def generate_fallback_description(field_name: str, data_type: str, table_name: str) -> str:
    """Generate a better fallback description when OpenAI fails."""
    field_lower = field_name.lower()
    
    # Common field patterns with short descriptions
    if 'id' in field_lower and ('customer' in field_lower or 'client' in field_lower):
        return "Customer unique identifier for record linking"
    elif 'id' in field_lower and field_lower.endswith('_id'):
        entity = field_name[:-3].replace('_', ' ').title()
        return f"Reference ID linking to {entity} records"
    elif 'amount' in field_lower or 'balance' in field_lower:
        return f"Monetary amount in base currency ({data_type})"
    elif 'date' in field_lower or 'time' in field_lower:
        return f"Date/time when event occurred ({data_type})"
    elif 'status' in field_lower or 'state' in field_lower:
        return "Status indicator for record state"
    elif 'code' in field_lower:
        return f"Standardized code for categorization ({data_type})"
    elif 'name' in field_lower or 'description' in field_lower:
        return f"Descriptive text information ({data_type})"
    elif 'account' in field_lower:
        return f"Account reference for financial operations ({data_type})"
    elif 'number' in field_lower:
        return f"Numeric identifier or sequence ({data_type})"
    else:
        # Generic short fallback
        clean_name = field_name.replace('_', ' ').title()
        return f"{clean_name} data field ({data_type})"

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
            table_description = generate_enhanced_banking_table_description(request.tableName, table_fields, source_system.name, source_system.description)
            
            # Generate field descriptions
            table_fields = generate_enhanced_banking_field_descriptions(request.tableName, table_fields, source_system.name, source_system.description)
            
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