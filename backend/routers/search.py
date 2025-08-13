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

def semantic_search_with_openai(query: str, items: List[dict], item_type: str) -> List[dict]:
    """Use OpenAI to perform semantic search and scoring"""
    try:
        # Create a prompt for OpenAI to analyze and score items
        items_text = "\n".join([
            f"{i+1}. {item['name']}: {item.get('description', 'No description')}"
            for i, item in enumerate(items)
        ])
        
        prompt = f"""You are analyzing a data dictionary search query. 

Query: "{query}"

Available {item_type}s:
{items_text}

Based on the search query, analyze which {item_type}s are most relevant. Consider:
- Direct name matches
- Semantic meaning and context
- Business domain relevance
- Functional relationships

Return a JSON array with objects containing:
- "index": the item number (1-based)
- "score": relevance score from 0.0 to 1.0
- "reason": brief explanation of relevance

Only include items with score >= 0.3. Sort by score descending.

IMPORTANT: Return ONLY the JSON array, no other text or formatting. Example:
[
  {"index": 6, "score": 1.0, "reason": "Exact match for RECID field"},
  {"index": 2, "score": 0.8, "reason": "Related record status field"}
]"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a data dictionary search expert. Analyze queries and match them to database objects based on semantic meaning, not just keyword matching."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        # Parse the response
        import json
        try:
            response_content = response.choices[0].message.content.strip()
            logger.debug(f"OpenAI response content: {response_content}")
            
            # Try to extract JSON from the response if it's wrapped in markdown or other text
            if "```json" in response_content:
                # Extract JSON from markdown code block
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                json_str = response_content[start:end].strip()
            elif response_content.startswith('[') or response_content.startswith('{'):
                # Response is already JSON
                json_str = response_content
            else:
                # Try to find JSON array in the response
                import re
                json_match = re.search(r'\[.*\]', response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.error(f"Could not extract JSON from OpenAI response: {response_content}")
                    return []
            
            scores = json.loads(json_str)
            
            # Apply scores to items
            scored_items = []
            for score_item in scores:
                index = score_item["index"] - 1  # Convert to 0-based
                if 0 <= index < len(items):
                    item = items[index].copy()
                    item["score"] = score_item["score"]
                    item["reason"] = score_item.get("reason", "")
                    scored_items.append(item)
            
            return sorted(scored_items, key=lambda x: x["score"], reverse=True)
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse OpenAI response as JSON. Content: {response.choices[0].message.content}")
            # Fallback to simple keyword matching
            return fallback_keyword_search(query, items, item_type)
        except Exception as e:
            logger.error(f"Error processing OpenAI response: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")

@router.post("/search", response_model=SearchResponse)
def fallback_keyword_search(query: str, items: List[dict], item_type: str) -> List[dict]:
    """Fallback keyword-based search when OpenAI fails"""
    try:
        query_lower = query.lower()
        query_words = query_lower.split()
        
        scored_items = []
        for item in items:
            score = 0.0
            name_lower = item['name'].lower()
            desc_lower = (item.get('description') or '').lower()
            
            # Exact name match gets highest score
            if query_lower == name_lower:
                score = 1.0
            # Name contains query gets high score
            elif query_lower in name_lower:
                score = 0.9
            # Query words in name
            elif any(word in name_lower for word in query_words):
                score = 0.8
            # Query in description
            elif query_lower in desc_lower:
                score = 0.7
            # Query words in description
            elif any(word in desc_lower for word in query_words):
                score = 0.6
            
            if score >= 0.3:
                item_copy = item.copy()
                item_copy["score"] = score
                item_copy["reason"] = f"Keyword match in {item_type} name/description"
                scored_items.append(item_copy)
        
        return sorted(scored_items, key=lambda x: x["score"], reverse=True)
        
    except Exception as e:
        logger.error(f"Error in fallback search: {str(e)}")
        return []

async def search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Processing search query: {request.query}")
        
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

        # Process tables with OpenAI semantic search
        if tables:
            table_items = []
            for table in tables:
                table_content = f"{table.name} - {table.description or ''} (Database: {table.database_name}, Source: {table.source_name})"
                table_items.append({
                    "id": str(table.id),
                    "name": table.name,
                    "description": table.description,
                    "databaseName": table.database_name,
                    "sourceName": table.source_name,
                    "content": table_content
                })
            
            # Use OpenAI for semantic search
            scored_tables = semantic_search_with_openai(request.query, table_items, "table")
            
            for table_item in scored_tables:
                if table_item["score"] >= request.min_score:
                    search_results.append(TableResult(
                        id=table_item["id"],
                        name=table_item["name"],
                        description=table_item["description"],
                        databaseName=table_item["databaseName"],
                        sourceName=table_item["sourceName"],
                        score=float(table_item["score"])
                    ))

        # Process fields with OpenAI semantic search
        if fields:
            field_items = []
            for field in fields:
                field_content = f"{field.name} ({field.type}) - {field.description or ''} (Table: {field.table_name}, Database: {field.database_name})"
                field_items.append({
                    "id": str(field.id),
                    "name": field.name,
                    "description": field.description,
                    "tableName": field.table_name,
                    "databaseName": field.database_name,
                    "sourceName": field.source_name,
                    "dataType": field.type,
                    "content": field_content
                })
            
            # Use OpenAI for semantic search
            scored_fields = semantic_search_with_openai(request.query, field_items, "field")
            
            for field_item in scored_fields:
                if field_item["score"] >= request.min_score:
                    search_results.append(FieldResult(
                        id=field_item["id"],
                        name=field_item["name"],
                        description=field_item["description"],
                        tableName=field_item["tableName"],
                        databaseName=field_item["databaseName"],
                        sourceName=field_item["sourceName"],
                        dataType=field_item["dataType"],
                        score=float(field_item["score"])
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