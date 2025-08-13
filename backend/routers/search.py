from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from typing import List, Optional
import logging
from openai import OpenAI
import numpy as np
from pydantic import BaseModel
from database import get_db
from models import SourceSystem, Database, Table, Field, Category
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    type_filter: Optional[str] = None
    source_filter: Optional[str] = None
    database_filter: Optional[str] = None
    min_score: Optional[float] = 0.7

class TableResult(BaseModel):
    type: str = "table"
    id: str
    name: str
    description: Optional[str] = None
    databaseName: str
    sourceName: str
    score: float

class FieldResult(BaseModel):
    type: str = "field"
    id: str
    name: str
    description: Optional[str] = None
    tableName: str
    databaseName: str
    sourceName: str
    dataType: str
    score: float

class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[TableResult | FieldResult]

def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI's API"""
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    a = np.array(embedding1)
    b = np.array(embedding2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Processing search query: {request.query}")
        
        # Get embedding for search query
        query_embedding = get_embedding(request.query)
        
        # Build base queries with joins
        table_query = """
            SELECT 
                t.id,
                t.name,
                t.description,
                d.name as database_name,
                s.name as source_name,
                c.name as category_name
            FROM tables t
            JOIN databases d ON t.database_id = d.id
            JOIN source_systems s ON d.source_id = s.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        
        field_query = """
            SELECT 
                f.id,
                f.name,
                f.description,
                f.type,
                t.name as table_name,
                d.name as database_name,
                s.name as source_name
            FROM fields f
            JOIN tables t ON f.table_id = t.id
            JOIN databases d ON t.database_id = d.id
            JOIN source_systems s ON d.source_id = s.id
            WHERE 1=1
        """
        
        # Apply filters
        params = {}
        if request.source_filter:
            table_query += " AND s.name = :source_name"
            field_query += " AND s.name = :source_name"
            params['source_name'] = request.source_filter
            
        if request.database_filter:
            table_query += " AND d.name = :database_name"
            field_query += " AND d.name = :database_name"
            params['database_name'] = request.database_filter

        # Execute queries
        tables = []
        fields = []
        
        if not request.type_filter or request.type_filter == 'table':
            tables = db.execute(text(table_query), params).fetchall()
            
        if not request.type_filter or request.type_filter == 'field':
            fields = db.execute(text(field_query), params).fetchall()

        search_results = []

        # Process tables
        for table in tables:
            # Create rich context for semantic search
            table_content = f"""
                Table Name: {table.name}
                Description: {table.description or ''}
                Database: {table.database_name}
                Source System: {table.source_name}
                Category: {table.category_name or 'Uncategorized'}
            """
            
            # Get embedding and calculate similarity
            table_embedding = get_embedding(table_content)
            similarity = cosine_similarity(query_embedding, table_embedding)

            if similarity >= request.min_score:
                search_results.append(TableResult(
                    id=str(table.id),
                    name=table.name,
                    description=table.description,
                    databaseName=table.database_name,
                    sourceName=table.source_name,
                    score=float(similarity)
                ))

        # Process fields
        for field in fields:
            # Create rich context for semantic search
            field_content = f"""
                Field Name: {field.name}
                Description: {field.description or ''}
                Data Type: {field.type}
                Table: {field.table_name}
                Database: {field.database_name}
                Source System: {field.source_name}
            """
            
            # Get embedding and calculate similarity
            field_embedding = get_embedding(field_content)
            similarity = cosine_similarity(query_embedding, field_embedding)

            if similarity >= request.min_score:
                search_results.append(FieldResult(
                    id=str(field.id),
                    name=field.name,
                    description=field.description,
                    tableName=field.table_name,
                    databaseName=field.database_name,
                    sourceName=field.source_name,
                    dataType=field.type,
                    score=float(similarity)
                ))

        # Sort results by similarity score
        search_results.sort(key=lambda x: x.score, reverse=True)
        
        # Log search metrics
        logger.info(f"Search completed. Found {len(search_results)} results")
        if search_results:
            logger.info(f"Top score: {search_results[0].score}")
        
        return SearchResponse(
            query=request.query,
            total=len(search_results),
            results=search_results[:20]  # Return top 20 results
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/suggestions")
async def get_search_suggestions(
    prefix: str,
    db: Session = Depends(get_db)
):
    """Get search suggestions based on prefix"""
    try:
        # Get matching table names
        table_suggestions = db.query(Table.name)\
            .filter(Table.name.ilike(f"%{prefix}%"))\
            .limit(5)\
            .all()
            
        # Get matching field names
        field_suggestions = db.query(Field.name)\
            .filter(Field.name.ilike(f"%{prefix}%"))\
            .limit(5)\
            .all()
            
        # Get matching categories
        category_suggestions = db.query(Category.name)\
            .filter(Category.name.ilike(f"%{prefix}%"))\
            .limit(5)\
            .all()
            
        return {
            "tables": [t[0] for t in table_suggestions],
            "fields": [f[0] for f in field_suggestions],
            "categories": [c[0] for c in category_suggestions]
        }
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/filters")
async def get_search_filters(db: Session = Depends(get_db)):
    """Get available search filters"""
    try:
        # Get unique source systems
        sources = db.query(SourceSystem.name).distinct().all()
        
        # Get unique databases
        databases = db.query(Database.name).distinct().all()
        
        # Get unique categories
        categories = db.query(Category.name).distinct().all()
        
        return {
            "sources": [s[0] for s in sources],
            "databases": [d[0] for d in databases],
            "categories": [c[0] for c in categories]
        }
        
    except Exception as e:
        logger.error(f"Error getting search filters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))