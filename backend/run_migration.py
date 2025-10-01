"""
Script to apply the table stats migration
"""
from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migration():
    with open('add_table_stats_columns.sql', 'r') as f:
        sql = f.read()

    try:
        with engine.connect() as conn:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for statement in statements:
                # Skip comments
                if statement and not statement.startswith('--'):
                    logger.info(f"Executing: {statement}")
                    conn.execute(text(statement))
                    conn.commit()

        logger.info("Migration applied successfully!")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    apply_migration()
