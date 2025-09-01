"""
AI-powered description generation using OpenAI with improved prompting
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
    """Generates AI-powered descriptions for tables and fields with improved business context"""
    
    @staticmethod
    def generate_table_description(
        table_name: str, 
        fields: List[TableField], 
        source_name: str, 
        source_description: str = None
    ) -> str:
        """Generate AI-powered table description with enhanced business context"""
        try:
            # Build comprehensive context
            context_parts = [f"Source System: {source_name}"]
            if source_description:
                context_parts.append(f"System Purpose: {source_description}")
            
            # Analyze field patterns for better context
            field_analysis = []
            key_fields = []
            data_patterns = []
            
            for field in fields:
                field_info = f"- {field.fieldName} ({field.dataType})"
                if field.isPrimaryKey == 'Yes':
                    field_info += " [Primary Key]"
                    key_fields.append(field.fieldName)
                if field.isForeignKey == 'Yes':
                    field_info += " [Foreign Key]"
                if field.isNullable == 'NO':
                    field_info += " [Required]"
                field_analysis.append(field_info)
                
                # Identify data patterns
                field_lower = field.fieldName.lower()
                if any(pattern in field_lower for pattern in ['date', 'time', 'created', 'updated', 'modified']):
                    data_patterns.append('temporal_data')
                elif any(pattern in field_lower for pattern in ['amount', 'balance', 'price', 'cost', 'fee']):
                    data_patterns.append('financial_data')
                elif any(pattern in field_lower for pattern in ['id', 'key', 'ref', 'code']):
                    data_patterns.append('identifier_data')
                elif any(pattern in field_lower for pattern in ['name', 'desc', 'title', 'label']):
                    data_patterns.append('descriptive_data')
            
            field_info = "\n".join(field_analysis)
            
            # Enhanced prompt with better context and examples
            prompt = f"""You are a senior data analyst specializing in business systems and data architecture.

CONTEXT:
Source System: {source_name}
{f"System Description: {source_description}" if source_description else ""}

TABLE TO ANALYZE:
Table Name: {table_name}

FIELD STRUCTURE:
{field_info}

ANALYSIS PATTERNS DETECTED:
- Key Fields: {', '.join(key_fields) if key_fields else 'None identified'}
- Data Types Present: {', '.join(set(data_patterns)) if data_patterns else 'Mixed data types'}

TASK:
Based on the source system context and table structure, provide a precise business description of what this table stores and its purpose.

REQUIREMENTS:
1. Focus on BUSINESS PURPOSE, not technical implementation
2. Use terminology appropriate to the source system type
3. Be specific about what business data/process this table supports
4. Maximum 80 characters
5. Use active, descriptive language

EXAMPLES OF GOOD DESCRIPTIONS:
- "Customer account master data for retail banking operations"
- "Daily transaction records for payment processing system"
- "Product catalog entries for e-commerce platform"
- "Employee payroll information for HR management"
- "Audit trail entries for compliance tracking"

EXAMPLES OF BAD DESCRIPTIONS:
- "Table containing data" (too generic)
- "Database table for storing information" (technical, not business-focused)
- "Data storage for various fields" (meaningless)

Provide ONLY the business description, no additional text or formatting."""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a business data analyst who creates precise, business-focused descriptions for database tables. You understand various business domains and can interpret table purposes from field structures and system context."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )

            description = response.choices[0].message.content.strip()
            # Clean up the description
            description = description.strip('"').strip("'").strip()
            
            # Ensure length constraint  
            if len(description) > 80:
                # Try to truncate at word boundary
                truncated = description[:77]
                last_space = truncated.rfind(' ')
                if last_space > 60:  # Only truncate at word boundary if it's not too short
                    description = truncated[:last_space] + '...'
                else:
                    description = truncated + '...'
            
            logger.info(f"Generated AI table description for {table_name}: {description}")
            return description

        except Exception as e:
            logger.error(f"Error generating AI table description: {str(e)}")
            # Enhanced fallback with better business context
            return BankingIntelligence.get_enhanced_table_fallback(table_name, source_name, fields)

    @staticmethod
    def generate_field_descriptions(
        table_name: str, 
        fields: List[TableField], 
        source_name: str, 
        source_description: str = None
    ) -> List[TableField]:
        """Generate AI-powered field descriptions with enhanced business context"""
        try:
            # Build comprehensive system context
            context_parts = [f"Source System: {source_name}"]
            if source_description:
                context_parts.append(f"System Purpose: {source_description}")
            
            system_context = "\n".join(context_parts)
            
            # Build enhanced field context with business intelligence
            fields_context = []
            for field in fields:
                context_line = f"- {field.fieldName} ({field.dataType})"
                
                # Add constraints and relationships
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
                
                # Add business intelligence hints
                field_hints = BankingIntelligence.get_field_business_hints(field.fieldName, field.dataType)
                if field_hints:
                    context_line += f" [Likely: {field_hints}]"
                
                fields_context.append(context_line)

            # Enhanced prompt with better business context
            prompt = f"""You are a senior business analyst specializing in data systems and business processes.

SYSTEM CONTEXT:
{system_context}

TABLE: {table_name}
FIELDS TO ANALYZE:
{chr(10).join(fields_context)}

TASK:
For each field, provide a precise business description that explains what the data represents and how it's used in the business context.

ANALYSIS GUIDELINES:
1. Use the source system information to understand business domain
2. Interpret field names in the business context (not just technical meaning)
3. Consider data types and constraints to understand field purpose
4. Focus on BUSINESS VALUE and USAGE, not technical implementation
5. Use terminology appropriate to the source system domain
6. Be specific about what business information the field contains

REQUIREMENTS:
- Maximum 50 characters per description
- Business-focused, not technical
- Use domain-appropriate terminology
- Format: "fieldName: description"
- Avoid generic phrases like "data field" or "information"

EXAMPLES OF GOOD DESCRIPTIONS:
- customer_id: Unique customer identifier
- account_balance: Current account balance amount
- transaction_date: Date transaction was processed
- interest_rate: Annual percentage rate applied
- branch_code: Bank branch identifier code
- status_flag: Account active/inactive indicator

EXAMPLES OF BAD DESCRIPTIONS:
- customer_id: Customer ID field (too generic)
- account_balance: Balance data (meaningless)
- transaction_date: Date field (technical, not business)

Provide descriptions for ALL fields in the exact format shown above."""

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a business data analyst who creates precise, business-focused descriptions for database fields. You understand various business domains and can interpret field purposes from names, types, and system context."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
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
                        # Try to truncate at word boundary
                        truncated = desc[:47]
                        last_space = truncated.rfind(' ')
                        if last_space > 35:  # Only truncate at word boundary if it's not too short
                            desc = truncated[:last_space] + '...'
                        else:
                            desc = truncated + '...'
                    
                    field_descriptions[field_name.strip()] = desc

            # Update field descriptions with enhanced fallbacks
            for field in fields:
                if field.fieldName in field_descriptions:
                    field.description = field_descriptions[field.fieldName]
                else:
                    # Enhanced fallback with business intelligence
                    field.description = BankingIntelligence.get_enhanced_field_fallback(
                        field.fieldName, field.dataType, source_name, table_name
                    )

            logger.info(f"Generated AI field descriptions for {len(fields)} fields in table {table_name}")
            return fields

        except Exception as e:
            logger.error(f"Error generating AI field descriptions: {str(e)}")
            # Enhanced fallback descriptions
            for field in fields:
                field.description = BankingIntelligence.get_enhanced_field_fallback(
                    field.fieldName, field.dataType, source_name, table_name
                )
            return fields