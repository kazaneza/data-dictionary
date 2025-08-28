"""
AI-powered description generation using OpenAI
"""

import logging
import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

from .models import TableField
from .banking_intelligence import BankingIntelligence

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class AIDescriptionGenerator:
    """Generates AI-powered descriptions for tables and fields"""
    
    @staticmethod
    def generate_table_description(
        table_name: str, 
        fields: List[TableField], 
        source_name: str, 
        source_description: str = None
    ) -> str:
        """Generate AI-powered table description with banking context"""
        try:
            # Get system context
            system_context = BankingIntelligence.get_system_context(source_name, source_description)
            
            # Build field analysis
            field_analysis = []
            for field in fields:
                analysis = f"- {field.fieldName} ({field.dataType})"
                
                if field.isPrimaryKey == 'Yes':
                    analysis += " [Primary Key]"
                if field.isForeignKey == 'Yes':
                    analysis += " [Foreign Key]"
                if field.isNullable == 'NO':
                    analysis += " [Required]"
                    
                field_analysis.append(analysis)
            
            field_info = "\n".join(field_analysis)
            
            prompt = f"""You are a senior database analyst specializing in banking and financial systems.

SOURCE SYSTEM CONTEXT:
{system_context}

ANALYZE THIS DATABASE TABLE:
Table Name: {table_name}

Field Structure:
{field_info}

TASK: Based on the source system information and table structure, provide a precise business description of what this table stores and its purpose.

ANALYSIS GUIDELINES:
1. Use the source system name and description to understand the business context
2. Analyze field names to understand the table's purpose (e.g., CUSTOMER_ID suggests customer data)
3. Consider field relationships (Primary Keys, Foreign Keys) to understand data flow
4. Focus on WHAT business data is stored, not technical implementation
5. Use appropriate business terminology based on the source system type

REQUIREMENTS:
- Maximum 80 characters
- Business-focused description
- Use terminology appropriate to the source system
- Be specific about the business function

EXAMPLES:
- "Customer account master data for retail banking operations"
- "Transaction entries for payment processing and settlement"
- "Loan application records for credit management system"

Provide ONLY the description, no additional text."""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a database analyst who creates concise, business-focused descriptions for database tables. You understand various banking and financial systems and can interpret table purposes from field structures and system context."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30,
                temperature=0.1
            )

            description = response.choices[0].message.content.strip()
            
            # Clean up the description
            description = description.strip('"').strip("'").strip()
            
            # Ensure length constraint  
            if len(description) > 80:
                description = description[:80].rsplit(' ', 1)[0] + '...'
            
            logger.info(f"Generated AI table description for {table_name}: {description}")
            return description

        except Exception as e:
            logger.error(f"Error generating AI table description: {str(e)}")
            # Fallback to simple description
            return BankingIntelligence.get_simple_table_fallback(table_name, source_name)

    @staticmethod
    def generate_field_descriptions(
        table_name: str, 
        fields: List[TableField], 
        source_name: str, 
        source_description: str = None
    ) -> List[TableField]:
        """Generate AI-powered field descriptions with system context"""
        try:
            # Get system context
            system_context = BankingIntelligence.get_system_context(source_name, source_description)
            
            # Build field context
            fields_context = []
            for field in fields:
                context_line = f"- {field.fieldName} ({field.dataType})"
                
                # Add constraints
                constraints = []
                if field.isPrimaryKey == 'Yes':
                    constraints.append("Primary Key")
                if field.isForeignKey == 'Yes':
                    constraints.append("Foreign Key")
                if field.isNullable == 'NO':
                    constraints.append("Required")
                if field.defaultValue:
                    constraints.append(f"Default: {field.defaultValue}")
                    
                if constraints:
                    context_line += f" [{', '.join(constraints)}]"
                    
                fields_context.append(context_line)

            prompt = f"""You are a database analyst specializing in banking and financial systems.

SOURCE SYSTEM CONTEXT:
{system_context}

ANALYZE THESE FIELDS IN TABLE: {table_name}

{chr(10).join(fields_context)}

TASK: For each field, provide a precise business description based on the source system context and field characteristics.

ANALYSIS GUIDELINES:
1. Use the source system information to understand business context
2. Interpret field names in the context of the source system (e.g., in T24: RC = Reconciliation, STMT = Statement)
3. Consider data types and constraints to understand field purpose
4. Use appropriate business terminology for the source system type
5. Focus on WHAT business data the field contains and HOW it's used

REQUIREMENTS:
- Maximum 50 characters per description
- Business-focused, not technical
- Use terminology appropriate to the source system
- Format: "fieldName: description"

EXAMPLES (adapt to your source system):
- CUSTOMER_ID: Unique customer identifier
- ACCOUNT_BALANCE: Current account balance amount
- TRANSACTION_DATE: Date of transaction processing
- MANDATE_REF: Payment authorization reference

Provide descriptions for ALL fields in the format shown above."""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a database analyst who creates concise, business-focused descriptions for database fields. You understand various banking and financial systems and can interpret field purposes from names, types, and system context."},
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
                    desc = description.strip().strip('"').strip("'")
                    # Ensure field description doesn't exceed 50 characters
                    if len(desc) > 50:
                        desc = desc[:50].rsplit(' ', 1)[0] + '...'
                    field_descriptions[field_name.strip()] = desc
            
            # Update field descriptions with fallbacks
            for field in fields:
                if field.fieldName in field_descriptions:
                    field.description = field_descriptions[field.fieldName]
                else:
                    field.description = BankingIntelligence.get_simple_fallback_description(
                        field.fieldName, field.dataType
                    )

            logger.info(f"Generated AI field descriptions for {len(fields)} fields in table {table_name}")
            return fields

        except Exception as e:
            logger.error(f"Error generating AI field descriptions: {str(e)}")
            # Fallback to simple descriptions
            for field in fields:
                field.description = BankingIntelligence.get_simple_fallback_description(
                    field.fieldName, field.dataType
                )
            return fields
"""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are a senior banking systems analyst specializing in {source_name}. You understand banking operations, regulatory requirements, and system architecture. Focus on business value and operational purpose."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=40,
                temperature=0.1
            )

            description = response.choices[0].message.content.strip()
            
            # Clean up the description
            description = description.strip('"').strip("'").strip()
            
            # Ensure length constraint  
            if len(description) > 100:
                description = description[:100].rsplit(' ', 1)[0] + '...'
            
            logger.info(f"Generated AI table description for {table_name}: {description}")
            return description

        except Exception as e:
            logger.error(f"Error generating AI table description: {str(e)}")
            # Fallback to banking intelligence
            return BankingIntelligence.get_table_fallback_description(table_name, fields, source_name)

    @staticmethod
    def generate_field_descriptions(
        table_name: str, 
        fields: List[TableField], 
        source_name: str, 
        source_description: str = None
    ) -> List[TableField]:
        """Generate AI-powered field descriptions with banking context"""
        try:
            # Get banking context
            system_context, field_hints = BankingIntelligence.get_system_context(source_name, source_description)
            
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

            prompt = f"""You are a senior banking systems analyst specializing in {source_name}.

BANKING SYSTEM CONTEXT:
- System: {source_name}
- Description: {source_description or 'Core banking system'}
- Technical Context: {system_context}

ANALYZE THESE FIELDS IN TABLE: {table_name}

{chr(10).join(fields_context)}

TASK: For each field, provide a precise business description that explains:
1. What specific banking data it contains
2. Its role in banking operations
3. How it's used in the business context

CONTEXT CLUES:
- Consider the source system's specific terminology
- Look for standard banking patterns (IDs, amounts, dates, codes)
- Think about the table's overall purpose
- Use proper banking domain language

REQUIREMENTS:
- Maximum 50 characters per description
- Business-focused, not technical
- Use proper banking terminology
- Format: "fieldName: description"

EXAMPLES:
- DD_MANDATE_REF: Direct debit mandate reference
- RC_DETAIL_ID: Reconciliation detail record identifier
- STMT_ENTRY_ID: Statement entry transaction identifier
- VALUE_DATE: Value date for interest calculation
"""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are a senior banking systems analyst with expertise in {source_name}. You understand banking operations, data flows, and business terminology. Focus on business purpose and operational context."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.2
            )

            # Parse response and update field descriptions
            response_text = response.choices[0].message.content.strip()
            description_lines = [line.strip() for line in response_text.split('\n') if line.strip() and ':' in line]
            
            field_descriptions = {}
            for line in description_lines:
                if ':' in line:
                    field_name, description = line.split(':', 1)
                    desc = description.strip().strip('"').strip("'")
                    # Ensure field description doesn't exceed 50 characters
                    if len(desc) > 50:
                        desc = desc[:50].rsplit(' ', 1)[0] + '...'
                    field_descriptions[field_name.strip()] = desc
            
            # Update field descriptions with banking-aware fallbacks
            for field in fields:
                if field.fieldName in field_descriptions:
                    field.description = field_descriptions[field.fieldName]
                else:
                    field.description = BankingIntelligence.get_field_fallback_description(
                        field.fieldName, field.dataType, table_name, source_name
                    )

            logger.info(f"Generated AI field descriptions for {len(fields)} fields in table {table_name}")
            return fields

        except Exception as e:
            logger.error(f"Error generating AI field descriptions: {str(e)}")
            # Fallback to banking intelligence
            for field in fields:
                field.description = BankingIntelligence.get_field_fallback_description(
                    field.fieldName, field.dataType, table_name, source_name
                )
            return fields