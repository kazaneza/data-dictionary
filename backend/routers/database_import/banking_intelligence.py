"""
Banking domain intelligence for generating contextual descriptions
"""

import logging
from typing import Dict, List, Tuple
from .models import TableField

logger = logging.getLogger(__name__)

class BankingIntelligence:
    """Banking domain knowledge for generating intelligent descriptions"""
    
    # Generic banking field patterns
    BANKING_FIELD_PATTERNS = {
        # Common banking abbreviations that appear across systems
        'AMT': 'Amount',
        'BAL': 'Balance', 
        'CCY': 'Currency',
        'LCY': 'Local Currency',
        'FCY': 'Foreign Currency',
        'TXN': 'Transaction',
        'ACCT': 'Account',
        'CUST': 'Customer',
        'REF': 'Reference',
        'ID': 'Identifier',
        'NO': 'Number',
        'DATE': 'Date',
        'TIME': 'Time',
        'STATUS': 'Status',
        'CODE': 'Code',
        'DESC': 'Description',
        'TYPE': 'Type',
        'RATE': 'Rate',
        'LIMIT': 'Limit',
        'CHARGE': 'Charge',
        'FEE': 'Fee',
        'DR': 'Debit',
        'CR': 'Credit'
    }

    @classmethod
    def get_system_context(cls, source_name: str, source_description: str = None) -> str:
        """Generate dynamic system context based on source information"""
        context_parts = []
        
        # Always include the source name
        context_parts.append(f"System Name: {source_name}")
        
        # Include source description if available
        if source_description and source_description.strip():
            context_parts.append(f"System Description: {source_description}")
        
        # Build comprehensive context
        system_context = "\n".join(context_parts)
        
        return system_context

    @classmethod
    def expand_banking_abbreviations(cls, text: str) -> str:
        """Expand common banking abbreviations in field names"""
        expanded_parts = []
        parts = text.replace('_', ' ').split()
        
        for part in parts:
            part_upper = part.upper()
            if part_upper in cls.BANKING_FIELD_PATTERNS:
                expanded_parts.append(cls.BANKING_FIELD_PATTERNS[part_upper])
            else:
                expanded_parts.append(part.lower())
        
        return ' '.join(expanded_parts)

    @classmethod
    def get_simple_fallback_description(cls, field_name: str, data_type: str) -> str:
        """Generate simple fallback description based on field name and data type"""
        # Expand abbreviations
        expanded_name = cls.expand_banking_abbreviations(field_name)
        
        # Add data type context
        if 'VARCHAR' in data_type.upper() or 'CHAR' in data_type.upper():
            return f"{expanded_name.title()} text field"
        elif 'NUMBER' in data_type.upper() or 'DECIMAL' in data_type.upper() or 'INT' in data_type.upper():
            return f"{expanded_name.title()} numeric value"
        elif 'DATE' in data_type.upper() or 'TIME' in data_type.upper():
            return f"{expanded_name.title()} date/time field"
        else:
            return f"{expanded_name.title()} data field"

    @classmethod
    def get_simple_table_fallback(cls, table_name: str, source_name: str) -> str:
        """Generate simple fallback description for tables"""
        clean_name = table_name.replace('_', ' ').lower()
        return f"{source_name} table for {clean_name} data management"