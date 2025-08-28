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
            # Get banking context
            system_context, field_hints = BankingIntelligence.get_system_context(source_name, source_description)
            table_context = BankingIntelligence.get_table_context(table_name, source_name, source_description)
            
            # Build field analysis with banking hints
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
System Context: {system_context}
Table Context: {table_context}

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