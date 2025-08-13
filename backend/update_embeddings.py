import os
import logging
from sqlalchemy import text
from openai import OpenAI
from database import SessionLocal, engine
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_embedding(text: str) -> bytes:
    """Get embedding for text using OpenAI's API"""
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        # Convert embedding to bytes for storage
        return bytes(str(response.data[0].embedding).encode())
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise

def update_table_embeddings():
    """Update embeddings for all tables"""
    db = SessionLocal()
    try:
        # Get all tables that need embeddings
        tables = db.execute(text("""
            SELECT 
                t.id,
                dbo.GenerateTableEmbeddingText(
                    t.name,
                    t.description,
                    d.name,
                    s.name,
                    ISNULL(c.name, 'Uncategorized')
                ) as embedding_text
            FROM tables t
            JOIN databases d ON t.database_id = d.id
            JOIN source_systems s ON d.source_id = s.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.embedding IS NULL
        """)).fetchall()

        for table in tables:
            try:
                embedding = get_embedding(table.embedding_text)
                db.execute(
                    text("UPDATE tables SET embedding = :embedding WHERE id = :id"),
                    {"embedding": embedding, "id": table.id}
                )
                db.commit()
                logger.info(f"Updated embedding for table {table.id}")
            except Exception as e:
                logger.error(f"Error updating table {table.id}: {str(e)}")
                db.rollback()

    finally:
        db.close()

def update_field_embeddings():
    """Update embeddings for all fields"""
    db = SessionLocal()
    try:
        # Get all fields that need embeddings
        fields = db.execute(text("""
            SELECT 
                f.id,
                dbo.GenerateFieldEmbeddingText(
                    f.name,
                    f.description,
                    f.type,
                    t.name,
                    d.name,
                    s.name
                ) as embedding_text
            FROM fields f
            JOIN tables t ON f.table_id = t.id
            JOIN databases d ON t.database_id = d.id
            JOIN source_systems s ON d.source_id = s.id
            WHERE f.embedding IS NULL
        """)).fetchall()

        for field in fields:
            try:
                embedding = get_embedding(field.embedding_text)
                db.execute(
                    text("UPDATE fields SET embedding = :embedding WHERE id = :id"),
                    {"embedding": embedding, "id": field.id}
                )
                db.commit()
                logger.info(f"Updated embedding for field {field.id}")
            except Exception as e:
                logger.error(f"Error updating field {field.id}: {str(e)}")
                db.rollback()

    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting embedding updates...")
    update_table_embeddings()
    update_field_embeddings()
    logger.info("Embedding updates completed")