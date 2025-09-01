"""
Enhanced banking domain intelligence for generating contextual descriptions
"""

import logging
from typing import Dict, List, Tuple
from .models import TableField

logger = logging.getLogger(__name__)

class BankingIntelligence:
    """Enhanced banking domain knowledge for generating intelligent descriptions"""
    
    # Enhanced banking field patterns with business context
    BUSINESS_FIELD_PATTERNS = {
        # Financial terms
        'AMT': 'Amount',
        'BAL': 'Balance', 
        'CCY': 'Currency',
        'LCY': 'Local Currency',
        'FCY': 'Foreign Currency',
        'RATE': 'Rate',
        'LIMIT': 'Limit',
        'CHARGE': 'Charge',
        'FEE': 'Fee',
        'COMMISSION': 'Commission',
        'INTEREST': 'Interest',
        'PRINCIPAL': 'Principal',
        'PENALTY': 'Penalty',
        
        # Transaction terms
        'TXN': 'Transaction',
        'TRANS': 'Transaction',
        'PAYMENT': 'Payment',
        'TRANSFER': 'Transfer',
        'DEPOSIT': 'Deposit',
        'WITHDRAWAL': 'Withdrawal',
        'CREDIT': 'Credit',
        'DEBIT': 'Debit',
        'DR': 'Debit',
        'CR': 'Credit',
        
        # Account terms
        'ACCT': 'Account',
        'ACCOUNT': 'Account',
        'PORTFOLIO': 'Portfolio',
        'POSITION': 'Position',
        'HOLDING': 'Holding',
        
        # Customer terms
        'CUST': 'Customer',
        'CLIENT': 'Client',
        'CUSTOMER': 'Customer',
        'PARTY': 'Party',
        'ENTITY': 'Entity',
        
        # Identification terms
        'ID': 'Identifier',
        'KEY': 'Key',
        'REF': 'Reference',
        'NO': 'Number',
        'NUM': 'Number',
        'CODE': 'Code',
        'MNEMONIC': 'Code',
        
        # Temporal terms
        'DATE': 'Date',
        'TIME': 'Time',
        'TIMESTAMP': 'Timestamp',
        'CREATED': 'Created',
        'UPDATED': 'Updated',
        'MODIFIED': 'Modified',
        'EFFECTIVE': 'Effective',
        'EXPIRY': 'Expiry',
        'MATURITY': 'Maturity',
        
        # Status and control
        'STATUS': 'Status',
        'STATE': 'State',
        'FLAG': 'Flag',
        'INDICATOR': 'Indicator',
        'ACTIVE': 'Active',
        'INACTIVE': 'Inactive',
        'ENABLED': 'Enabled',
        'DISABLED': 'Disabled',
        
        # Descriptive terms
        'DESC': 'Description',
        'DESCRIPTION': 'Description',
        'NAME': 'Name',
        'TITLE': 'Title',
        'LABEL': 'Label',
        'COMMENT': 'Comment',
        'REMARKS': 'Remarks',
        'NOTES': 'Notes',
        
        # Business specific
        'BRANCH': 'Branch',
        'DEPARTMENT': 'Department',
        'PRODUCT': 'Product',
        'SERVICE': 'Service',
        'CHANNEL': 'Channel',
        'CATEGORY': 'Category',
        'TYPE': 'Type',
        'CLASS': 'Class',
        'GRADE': 'Grade',
        'LEVEL': 'Level'
    }

    # Business context patterns for different domains
    DOMAIN_CONTEXTS = {
        'banking': {
            'keywords': ['bank', 'account', 'transaction', 'customer', 'loan', 'deposit'],
            'purpose': 'financial services and banking operations'
        },
        'payment': {
            'keywords': ['payment', 'transfer', 'settlement', 'clearing'],
            'purpose': 'payment processing and settlement'
        },
        'risk': {
            'keywords': ['risk', 'compliance', 'audit', 'control'],
            'purpose': 'risk management and compliance'
        },
        'customer': {
            'keywords': ['customer', 'client', 'party', 'relationship'],
            'purpose': 'customer relationship management'
        },
        'product': {
            'keywords': ['product', 'service', 'offering', 'catalog'],
            'purpose': 'product and service management'
        }
    }

    @classmethod
    def get_system_context(cls, source_name: str, source_description: str = None) -> str:
        """Generate enhanced system context based on source information"""
        context_parts = []
        
        # Always include the source name
        context_parts.append(f"System Name: {source_name}")
        
        # Include source description if available
        if source_description and source_description.strip():
            context_parts.append(f"System Description: {source_description}")
        
        # Detect domain context
        domain_context = cls._detect_domain_context(source_name, source_description)
        if domain_context:
            context_parts.append(f"Business Domain: {domain_context}")
        
        return "\n".join(context_parts)

    @classmethod
    def _detect_domain_context(cls, source_name: str, source_description: str = None) -> str:
        """Detect business domain context from source information"""
        text_to_analyze = f"{source_name} {source_description or ''}".lower()
        
        domain_scores = {}
        for domain, config in cls.DOMAIN_CONTEXTS.items():
            score = sum(1 for keyword in config['keywords'] if keyword in text_to_analyze)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            best_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
            return cls.DOMAIN_CONTEXTS[best_domain]['purpose']
        
        return None

    @classmethod
    def get_field_business_hints(cls, field_name: str, data_type: str) -> str:
        """Get business hints for a field based on name and type patterns"""
        field_upper = field_name.upper()
        hints = []
        
        # Check for business patterns in field name
        for pattern, meaning in cls.BUSINESS_FIELD_PATTERNS.items():
            if pattern in field_upper:
                hints.append(meaning.lower())
        
        # Add data type context
        if 'DECIMAL' in data_type.upper() or 'MONEY' in data_type.upper():
            hints.append('monetary value')
        elif 'DATE' in data_type.upper() or 'TIME' in data_type.upper():
            hints.append('temporal data')
        elif 'CHAR' in data_type.upper() or 'VARCHAR' in data_type.upper():
            if any(term in field_upper for term in ['CODE', 'ID', 'KEY']):
                hints.append('identifier')
            else:
                hints.append('text data')
        
        return ', '.join(hints[:2]) if hints else None

    @classmethod
    def expand_banking_abbreviations(cls, text: str) -> str:
        """Expand common banking abbreviations in field names"""
        expanded_parts = []
        parts = text.replace('_', ' ').split()
        
        for part in parts:
            part_upper = part.upper()
            if part_upper in cls.BUSINESS_FIELD_PATTERNS:
                expanded_parts.append(cls.BUSINESS_FIELD_PATTERNS[part_upper])
            else:
                expanded_parts.append(part.lower())
        
        return ' '.join(expanded_parts)

    @classmethod
    def get_enhanced_field_fallback(cls, field_name: str, data_type: str, source_name: str, table_name: str) -> str:
        """Generate enhanced fallback description with business context"""
        # Expand abbreviations
        expanded_name = cls.expand_banking_abbreviations(field_name)
        
        # Get business hints
        hints = cls.get_field_business_hints(field_name, data_type)
        
        # Build context-aware description
        if hints:
            if 'identifier' in hints:
                return f"Unique {expanded_name} identifier"
            elif 'monetary' in hints:
                return f"{expanded_name.title()} monetary value"
            elif 'temporal' in hints:
                return f"{expanded_name.title()} timestamp"
            else:
                return f"{expanded_name.title()} business data"
        else:
            # Standard fallback with data type context
            if 'VARCHAR' in data_type.upper() or 'CHAR' in data_type.upper():
                return f"{expanded_name.title()} text field"
            elif 'NUMBER' in data_type.upper() or 'DECIMAL' in data_type.upper() or 'INT' in data_type.upper():
                return f"{expanded_name.title()} numeric value"
            elif 'DATE' in data_type.upper() or 'TIME' in data_type.upper():
                return f"{expanded_name.title()} date/time field"
            else:
                return f"{expanded_name.title()} data field"

    @classmethod
    def get_enhanced_table_fallback(cls, table_name: str, source_name: str, fields: List[TableField]) -> str:
        """Generate enhanced fallback description for tables with field analysis"""
        # Analyze fields to understand table purpose
        field_patterns = []
        for field in fields:
            field_upper = field.fieldName.upper()
            if any(pattern in field_upper for pattern in ['CUSTOMER', 'CLIENT', 'PARTY']):
                field_patterns.append('customer')
            elif any(pattern in field_upper for pattern in ['ACCOUNT', 'ACCT']):
                field_patterns.append('account')
            elif any(pattern in field_upper for pattern in ['TRANSACTION', 'TXN', 'TRANS']):
                field_patterns.append('transaction')
            elif any(pattern in field_upper for pattern in ['PRODUCT', 'SERVICE']):
                field_patterns.append('product')
            elif any(pattern in field_upper for pattern in ['AUDIT', 'LOG', 'HISTORY']):
                field_patterns.append('audit')
        
        # Generate description based on patterns
        if field_patterns:
            primary_pattern = max(set(field_patterns), key=field_patterns.count)
            clean_table_name = table_name.replace('_', ' ').lower()
            return f"{source_name} {primary_pattern} data for {clean_table_name} management"
        else:
            clean_table_name = table_name.replace('_', ' ').lower()
            return f"{source_name} data table for {clean_table_name} operations"

    @classmethod
    def get_simple_fallback_description(cls, field_name: str, data_type: str) -> str:
        """Generate simple fallback description (kept for backward compatibility)"""
        return cls.get_enhanced_field_fallback(field_name, data_type, "System", "table")

    @classmethod
    def get_simple_table_fallback(cls, table_name: str, source_name: str) -> str:
        """Generate simple fallback description for tables (kept for backward compatibility)"""
        clean_name = table_name.replace('_', ' ').lower()
        return f"{source_name} table for {clean_name} data management"