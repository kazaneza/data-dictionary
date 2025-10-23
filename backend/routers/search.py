from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from typing import List, Optional, Union
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

class NaturalLanguageFieldRequest(BaseModel):
    query: str
    source_filter: Optional[str] = None
    database_filter: Optional[str] = None
    limit: Optional[int] = 20

class FieldMatch(BaseModel):
    id: str
    name: str
    description: Optional[str]
    tableName: str
    databaseName: str
    sourceName: str
    dataType: str
    score: float
    reason: str

class NaturalLanguageFieldResponse(BaseModel):
    query: str
    interpretation: str
    total: int
    results: List[FieldMatch]

@router.post("/search/natural-language-fields", response_model=NaturalLanguageFieldResponse)
async def natural_language_field_search(
    request: NaturalLanguageFieldRequest,
    db: Session = Depends(get_db)
):
    """
    Search for fields using natural language description.
    Example: "I want a field for a customer legal document"
    """
    try:
        # First, interpret the query using OpenAI to understand what the user is looking for
        interpretation_prompt = f"""You are a data dictionary expert. A user is searching for database fields using natural language.

User query: "{request.query}"

Analyze this query and provide:
1. What type of data the user is looking for
2. Key concepts and terms to search for
3. Related business domains

Respond in JSON format:
{{
  "interpretation": "Brief explanation of what the user is looking for",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "domains": ["business domain1", "business domain2"]
}}"""

        interpretation_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a data dictionary search expert specializing in understanding natural language queries about database fields."},
                {"role": "user", "content": interpretation_prompt}
            ],
            max_tokens=500,
            temperature=0.2
        )

        import json
        interpretation_text = interpretation_response.choices[0].message.content.strip()
        if "```json" in interpretation_text:
            start = interpretation_text.find("```json") + 7
            end = interpretation_text.find("```", start)
            interpretation_text = interpretation_text[start:end].strip()

        interpretation_data = json.loads(interpretation_text)
        interpretation = interpretation_data.get("interpretation", "Searching for relevant fields")

        # Build query to get all fields
        query = db.query(
            Field.id,
            Field.name,
            Field.description,
            Field.type,
            Table.name.label('table_name'),
            Database.name.label('database_name'),
            SourceSystem.name.label('source_name')
        ).join(Table, Field.table_id == Table.id)\
         .join(Database, Table.database_id == Database.id)\
         .join(SourceSystem, Database.source_id == SourceSystem.id)

        # Apply filters if provided
        if request.source_filter:
            query = query.filter(SourceSystem.name == request.source_filter)
        if request.database_filter:
            query = query.filter(Database.name == request.database_filter)

        all_fields = query.all()

        # Convert to dictionaries for AI processing
        fields_data = []
        for field in all_fields:
            fields_data.append({
                'id': str(field.id),
                'name': field.name,
                'description': field.description or 'No description',
                'dataType': field.type,
                'tableName': field.table_name,
                'databaseName': field.database_name,
                'sourceName': field.source_name
            })

        if not fields_data:
            return NaturalLanguageFieldResponse(
                query=request.query,
                interpretation=interpretation,
                total=0,
                results=[]
            )

        # Use OpenAI to match fields to the query
        fields_text = "\n".join([
            f"{i+1}. {f['name']} ({f['dataType']}) in {f['tableName']}: {f['description']}"
            for i, f in enumerate(fields_data[:500])  # Limit to prevent token overflow
        ])

        matching_prompt = f"""You are analyzing a natural language query to find matching database fields.

User query: "{request.query}"
Interpretation: {interpretation}

Available fields (showing up to 500):
{fields_text}

Based on the query, identify the most relevant fields. Consider:
- Semantic meaning of field names
- Field descriptions and their relevance
- Data types that match the query intent
- Business context and domain relevance
- Table context

Return a JSON array with objects containing:
- "index": the field number (1-based)
- "score": relevance score from 0.0 to 1.0 (0.8+ for highly relevant, 0.6-0.8 for relevant, 0.4-0.6 for possibly relevant)
- "reason": brief explanation of why this field matches

Only include fields with score >= 0.4. Sort by score descending. Limit to top {request.limit} matches.

Example:
[
  {{"index": 15, "score": 0.95, "reason": "CustomerLegalDocument field directly matches the requirement"}},
  {{"index": 8, "score": 0.85, "reason": "DocumentType field is relevant for categorizing legal documents"}}
]"""

        matching_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a database field matching expert. Analyze queries and match them to database fields based on semantic meaning and business context."},
                {"role": "user", "content": matching_prompt}
            ],
            max_tokens=3000,
            temperature=0.1
        )

        # Parse the AI response
        response_content = matching_response.choices[0].message.content.strip()
        logger.info(f"AI matching response: {response_content}")

        if "```json" in response_content:
            start = response_content.find("```json") + 7
            end = response_content.find("```", start)
            json_str = response_content[start:end].strip()
        elif response_content.startswith('['):
            json_str = response_content
        else:
            import re
            json_match = re.search(r'\[.*\]', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                logger.error(f"Could not extract JSON from response: {response_content}")
                return NaturalLanguageFieldResponse(
                    query=request.query,
                    interpretation=interpretation,
                    total=0,
                    results=[]
                )

        matches = json.loads(json_str)

        # Build result list
        results = []
        for match in matches[:request.limit]:
            index = match["index"] - 1
            if 0 <= index < len(fields_data):
                field_data = fields_data[index]
                results.append(FieldMatch(
                    id=field_data['id'],
                    name=field_data['name'],
                    description=field_data['description'],
                    tableName=field_data['tableName'],
                    databaseName=field_data['databaseName'],
                    sourceName=field_data['sourceName'],
                    dataType=field_data['dataType'],
                    score=match["score"],
                    reason=match["reason"]
                ))

        return NaturalLanguageFieldResponse(
            query=request.query,
            interpretation=interpretation,
            total=len(results),
            results=results
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from AI response: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process AI response")
    except Exception as e:
        logger.error(f"Error in natural language field search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))