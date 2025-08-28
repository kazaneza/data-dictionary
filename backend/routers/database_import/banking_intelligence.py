"""
Banking domain intelligence for generating contextual descriptions
"""

import logging
from typing import Dict, List, Tuple
from .models import TableField

logger = logging.getLogger(__name__)

class BankingIntelligence:
    """Banking domain knowledge for generating intelligent descriptions"""
    
    # Banking system patterns and terminology
    BANKING_PATTERNS = {
        'temenos': {
            'system_type': 'Temenos T24 Core Banking',
            'table_patterns': {
                'STMT': 'Statement processing and account statement generation',
                'AC': 'Account management and customer account operations',
                'FT': 'Funds transfer and payment processing',
                'AA': 'Arrangement Architecture for loans and deposits',
                'CU': 'Customer information management',
                'MM': 'Money market and treasury operations',
                'SC': 'Securities and investment management',
                'PD': 'Product definition and configuration',
                'LD': 'Loans and deposits management',
                'DE': 'Deal entry and transaction capture',
                'RE': 'Reporting and regulatory compliance',
                'ST': 'Standing instructions and automated payments',
                'TF': 'Trade finance operations',
                'FX': 'Foreign exchange trading',
                'PP': 'Payment processing',
                'LI': 'Limits management and credit control',
                'EB': 'External banking interfaces',
                'AI': 'Account information services',
                'RC': 'Reconciliation and matching operations'
            },
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
                'FX': 'Foreign Exchange',
                'PP': 'Payment Processing',
                'LI': 'Limits Management',
                'EB': 'External Banking',
                'AI': 'Account Information',
                'RC': 'Reconciliation',
                'STMT': 'Statement Processing'
            },
            'field_patterns': {
                'DETAIL.ID': 'Unique identifier for detail record linkage',
                'ENTRY.ID': 'Unique identifier for transaction entry record',
                'MANDATE.REF': 'Reference to payment mandate or authorization',
                'STMT.ID': 'Statement identifier for account statement',
                'RC.ID': 'Reconciliation record identifier',
                'TXN.REF': 'Transaction reference number',
                'DEAL.REF': 'Deal or contract reference identifier',
                'CUSTOMER.NO': 'Customer number in T24 system',
                'ACCOUNT.NO': 'Account number identifier',
                'PRODUCT.GROUP': 'Banking product group classification',
                'VALUE.DATE': 'Value date for interest calculation',
                'BOOKING.DATE': 'Transaction booking date',
                'PROCESSING.DATE': 'Date when transaction was processed',
                'NARRATIVE': 'Transaction description or narrative text',
                'DEBIT.CREDIT': 'Transaction direction indicator',
                'THEIR.REFERENCE': 'External party reference number',
                'OUR.REFERENCE': 'Internal bank reference number',
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
                'COMM': 'Commission',
                'TENOR': 'Term/Period',
                'MATURITY': 'Maturity Date',
                'VALUE': 'Value Date',
                'BOOKING': 'Booking Date',
                'SETTLEMENT': 'Settlement',
                'CLEARING': 'Clearing',
                'BRANCH': 'Branch Code',
                'GL': 'General Ledger',
                'NOSTRO': 'Nostro Account',
                'VOSTRO': 'Vostro Account'
            }
        }
    }
    
    # Generic banking field patterns
    BANKING_FIELD_PATTERNS = {
        'DD_MANDATE_REF': 'Direct debit mandate reference for payment authorization',
        'RC_DETAIL_ID': 'Reconciliation detail record identifier for audit trail',
        'STMT_ENTRY_ID': 'Statement entry identifier for transaction records',
        'MANDATE_REF': 'Payment mandate reference for authorization tracking',
        'DETAIL_ID': 'Detail record identifier for data linkage',
        'ENTRY_ID': 'Entry record identifier for transaction tracking',
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
    
    # Banking table patterns
    BANKING_TABLE_PATTERNS = {
        'STMT': 'Statement processing and account statement generation',
        'ENTRY': 'Transaction entry records and posting details',
        'MANDATE': 'Payment mandate and authorization management',
        'RECONCILIATION': 'Account reconciliation and matching operations',
        'RC': 'Reconciliation and matching operations',
        'CUSTOMER': 'Stores customer information and relationship data for banking services',
        'CLIENT': 'Stores customer information and relationship data for banking services',
        'ACCOUNT': 'Manages bank account details, balances, and account-related information',
        'TRANSACTION': 'Records financial transactions and money movement activities',
        'TXN': 'Records financial transactions and money movement activities',
        'TRANS': 'Records financial transactions and money movement activities',
        'LOAN': 'Manages loan accounts, credit facilities, and lending operations',
        'CREDIT': 'Manages loan accounts, credit facilities, and lending operations',
        'DEPOSIT': 'Handles deposit accounts and savings product information',
        'SAVINGS': 'Handles deposit accounts and savings product information',
        'PAYMENT': 'Processes payment instructions and settlement transactions',
        'PAY': 'Processes payment instructions and settlement transactions',
        'RATE': 'Stores interest rates and pricing information for banking products',
        'INTEREST': 'Stores interest rates and pricing information for banking products',
        'LIMIT': 'Defines transaction limits and operational thresholds',
        'THRESHOLD': 'Defines transaction limits and operational thresholds',
        'CHARGE': 'Manages fees, charges, and commission structures',
        'FEE': 'Manages fees, charges, and commission structures',
        'COMM': 'Manages fees, charges, and commission structures'
    }

    @classmethod
    def get_system_context(cls, source_name: str, source_description: str = None) -> Tuple[str, Dict[str, str]]:
        """Get banking system context and field hints"""
        source_lower = source_name.lower()
        desc_lower = (source_description or '').lower()
        
        # Check for Temenos/T24
        if any(term in source_lower or term in desc_lower for term in ['temenos', 't24']):
            context = cls.BANKING_PATTERNS['temenos']
            system_context = f"This is a {context['system_type']} system. T24 uses specific module prefixes and field naming conventions for banking operations."
            return system_context, context['field_patterns']
        
        # Generic banking system
        elif any(term in source_lower or term in desc_lower for term in ['core banking', 'banking', 'bank']):
            return "This is a Core Banking System handling customer accounts, transactions, loans, and deposits.", {}
        
        # Payment system
        elif any(term in source_lower or term in desc_lower for term in ['payment', 'swift', 'ach', 'wire']):
            return "This is a Payment Processing System handling money transfers, settlements, and clearing operations.", {}
        
        # Default banking context
        else:
            return f"This is a banking/financial system called '{source_name}'. Analyze the table and field names to understand the business domain.", {}

    @classmethod
    def get_table_context(cls, table_name: str, source_name: str, source_description: str = None) -> str:
        """Get specific context for a table based on banking patterns"""
        table_upper = table_name.upper()
        source_lower = source_name.lower()
        
        # Temenos-specific table analysis
        if any(term in source_lower for term in ['temenos', 't24']):
            # Check for full table name patterns first
            temenos_tables = cls.BANKING_PATTERNS['temenos']['table_patterns']
            for pattern, description in temenos_tables.items():
                if pattern in table_upper:
                    return f"T24 {description} module table"
            
            # Then check prefixes
            table_prefix = table_name.split('_')[0].upper() if '_' in table_name else table_name[:2].upper()
            temenos_prefixes = cls.BANKING_PATTERNS['temenos']['common_prefixes']
            
            if table_prefix in temenos_prefixes:
                return f"This table is part of {temenos_prefixes[table_prefix]} module in Temenos T24."
        
        # Generic banking table patterns
        for pattern, description in cls.BANKING_TABLE_PATTERNS.items():
            if pattern in table_upper:
                return f"Banking table: {description}"
        
        return f"Banking system table for {table_name.replace('_', ' ').lower()} operations"

    @classmethod
    def get_field_fallback_description(cls, field_name: str, data_type: str, table_name: str, source_name: str) -> str:
        """Generate banking-specific fallback descriptions for fields"""
        field_upper = field_name.upper()
        
        # Check exact matches first
        if field_upper in cls.BANKING_FIELD_PATTERNS:
            return cls.BANKING_FIELD_PATTERNS[field_upper]
        
        # Check for Temenos-specific patterns
        source_lower = source_name.lower()
        if any(term in source_lower for term in ['temenos', 't24']):
            temenos_patterns = cls.BANKING_PATTERNS['temenos']['field_patterns']
            for pattern, meaning in temenos_patterns.items():
                if pattern in field_upper:
                    return meaning
        # Pattern matching for partial matches
        if 'CUSTOMER' in field_upper and 'ID' in field_upper:
            return 'Customer unique identifier'
        elif 'ACCOUNT' in field_upper and 'ID' in field_upper:
            return 'Account unique identifier'
        elif 'MANDATE' in field_upper and 'REF' in field_upper:
            return 'Payment mandate reference for authorization'
        elif 'DETAIL' in field_upper and 'ID' in field_upper:
            return 'Detail record identifier for data linkage'
        elif 'ENTRY' in field_upper and 'ID' in field_upper:
            return 'Entry record identifier for transaction tracking'
        elif 'RC' in field_upper and 'ID' in field_upper:
            return 'Reconciliation record identifier'
        elif 'BALANCE' in field_upper or 'BAL' in field_upper:
            return 'Account balance amount'
        elif 'AMOUNT' in field_upper or 'AMT' in field_upper:
            return 'Monetary amount value'
        elif 'DATE' in field_upper:
            if 'VALUE' in field_upper:
                return 'Value date for interest calculation'
            elif 'BOOKING' in field_upper:
                return 'Transaction booking date'
            elif 'PROCESSING' in field_upper:
                return 'Date when transaction was processed'
            else:
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

    @classmethod
    def get_table_fallback_description(cls, table_name: str, fields: List[TableField], source_name: str) -> str:
        """Generate banking-specific fallback descriptions for tables"""
        table_upper = table_name.upper()
        
        # Check banking table patterns
        for pattern, description in cls.BANKING_TABLE_PATTERNS.items():
            if pattern in table_upper:
                return description
        
        # Fallback based on source system
        source_lower = source_name.lower()
        if 'temenos' in source_lower or 't24' in source_lower:
            return f"Temenos T24 data table for {table_name.replace('_', ' ').lower()} management"
        else:
            return f"Banking system table for {table_name.replace('_', ' ').lower()} operations"