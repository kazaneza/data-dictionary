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
    metadata_confidence: Optional[str] = "unknown"  # high/medium/low/unknown
    is_primary_key: Optional[bool] = False
    is_nullable: Optional[bool] = True

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
        import json

        # First, interpret the query using OpenAI to extract precise intent
        interpretation_prompt = f"""You are a database search expert analyzing a query for semantic field matching.

User query: "{request.query}"

Extract the PRECISE business concept and related terms:

1. Core Concept: The exact business meaning (e.g., "employment status" not just "status")
2. Primary Keywords: Specific terms and word stems that define this concept (5-8 keywords)
3. Related Terms: Synonyms, variants, and domain-specific jargon (3-5 terms)
4. Exclusion Keywords: Generic terms that could cause false matches (e.g., if looking for "employment status", exclude generic "status", "active", "inactive" unless combined with employment context)
5. Primary Entities: What database objects would likely store this (e.g., "Customer", "Employee", "Account")
6. Secondary Entities: Related objects that might reference this indirectly

Respond in JSON format:
{{
  "interpretation": "Precise business concept explanation",
  "core_concept": "exact_concept_name",
  "primary_keywords": ["specific_term1", "specific_term2"],
  "related_terms": ["synonym1", "variant1"],
  "exclusion_keywords": ["generic_term1", "confusing_term1"],
  "primary_entities": ["EntityName1", "EntityName2"],
  "secondary_entities": ["RelatedEntity1"]
}}

Example for "customer employment status":
{{
  "interpretation": "Customer's current employment classification and job status",
  "core_concept": "employment_status",
  "primary_keywords": ["employment", "employ", "job", "work", "occupation", "profession", "career"],
  "related_terms": ["employed", "employer", "employee", "occupation_type", "work_status"],
  "exclusion_keywords": ["account_status", "loan_status", "application_status", "marital_status", "address_status"],
  "primary_entities": ["Customer", "Client", "Borrower", "Applicant"],
  "secondary_entities": ["Employment", "Income", "Occupation"]
}}"""

        interpretation_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a data dictionary search expert specializing in precise semantic analysis of database field queries. Focus on specificity over generality."},
                {"role": "user", "content": interpretation_prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )

        interpretation_text = interpretation_response.choices[0].message.content.strip()
        if "```json" in interpretation_text:
            start = interpretation_text.find("```json") + 7
            end = interpretation_text.find("```", start)
            interpretation_text = interpretation_text[start:end].strip()

        interpretation_data = json.loads(interpretation_text)
        interpretation = interpretation_data.get("interpretation", "Searching for relevant fields")
        core_concept = interpretation_data.get("core_concept", "")
        primary_keywords = interpretation_data.get("primary_keywords", [])
        related_terms = interpretation_data.get("related_terms", [])
        exclusion_keywords = [x.lower() for x in interpretation_data.get("exclusion_keywords", [])]
        primary_entities = [x.lower() for x in interpretation_data.get("primary_entities", [])]
        secondary_entities = [x.lower() for x in interpretation_data.get("secondary_entities", [])]

        # Combine for keyword matching
        all_keywords = primary_keywords + related_terms

        logger.info(f"Intent Analysis - Core: {core_concept}")
        logger.info(f"Primary Keywords: {primary_keywords}")
        logger.info(f"Exclusions: {exclusion_keywords}")
        logger.info(f"Primary Entities: {primary_entities}")

        # Build query to get all fields with metadata
        query = db.query(
            Field.id,
            Field.name,
            Field.description,
            Field.type,
            Field.is_primary_key,
            Field.nullable,
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

        if not all_fields:
            return NaturalLanguageFieldResponse(
                query=request.query,
                interpretation=interpretation,
                total=0,
                results=[]
            )

        # Advanced scoring with intent focus, entity scoping, and exclusion logic
        def advanced_keyword_score(field):
            score = 0
            penalties = 0

            name_lower = field.name.lower()
            desc_lower = (field.description or '').lower()
            table_lower = field.table_name.lower()

            # Combine field and table for compound matching
            full_context = f"{table_lower}.{name_lower} {desc_lower}"

            # === EXCLUSION LOGIC (check first, apply penalties) ===
            exclusion_found = False
            for exclusion in exclusion_keywords:
                # Only penalize if exclusion term appears WITHOUT primary keywords
                if exclusion in full_context:
                    # Check if any primary keyword is nearby to provide context
                    has_context = False
                    for pk in primary_keywords:
                        if pk.lower() in full_context:
                            has_context = True
                            break

                    if not has_context:
                        penalties += 30
                        exclusion_found = True
                        logger.debug(f"Exclusion penalty for {table_lower}.{name_lower}: found '{exclusion}' without context")

            # === ENTITY SCOPING (prioritize primary entities) ===
            entity_boost = 0
            for entity in primary_entities:
                if entity in table_lower:
                    entity_boost += 40  # Strong boost for primary entity tables
                    logger.debug(f"Primary entity boost for {table_lower}: matched '{entity}'")
                elif entity in name_lower:
                    entity_boost += 20  # Moderate boost for entity in field name

            for entity in secondary_entities:
                if entity in table_lower:
                    entity_boost += 15  # Smaller boost for secondary entities
                elif entity in name_lower:
                    entity_boost += 8

            score += entity_boost

            # === CORE CONCEPT MATCHING (highest priority) ===
            if core_concept:
                core_lower = core_concept.lower()
                # Exact match in field name
                if core_lower == name_lower or core_lower.replace('_', '') == name_lower.replace('_', ''):
                    score += 100  # Perfect match
                    logger.debug(f"EXACT core concept match: {name_lower}")
                # Field name contains core concept
                elif core_lower in name_lower:
                    score += 60
                # Core concept in table.field combination
                elif core_lower in f"{table_lower}_{name_lower}":
                    score += 50
                # Core concept in description
                elif core_lower in desc_lower:
                    score += 20

            # === PRIMARY KEYWORDS (multi-word presence = compound boost) ===
            primary_matches = 0
            primary_match_positions = []

            for idx, keyword in enumerate(primary_keywords):
                kw_lower = keyword.lower()

                # Prefix matching (employ matches employment, employed)
                if name_lower.startswith(kw_lower) or f"_{kw_lower}" in name_lower:
                    score += 45
                    primary_matches += 1
                    primary_match_positions.append('field_prefix')
                # Exact word in field name
                elif kw_lower == name_lower or f"_{kw_lower}_" in name_lower or name_lower.endswith(f"_{kw_lower}"):
                    score += 40
                    primary_matches += 1
                    primary_match_positions.append('field_exact')
                # Substring in field name
                elif kw_lower in name_lower:
                    score += 25
                    primary_matches += 1
                    primary_match_positions.append('field_substring')

                # Table name matches (crucial context)
                if kw_lower in table_lower:
                    score += 30
                    primary_matches += 1
                    primary_match_positions.append('table')

                # Description matches (lower weight)
                if kw_lower in desc_lower:
                    score += 8

            # Compound keyword bonus (multiple keywords present = higher confidence)
            if primary_matches >= 2:
                score += 30 * (primary_matches - 1)  # Exponential boost
                logger.debug(f"Compound keyword bonus for {name_lower}: {primary_matches} keywords")

            # === RELATED TERMS (synonym matching) ===
            for term in related_terms:
                term_lower = term.lower()
                if term_lower in name_lower:
                    score += 15
                elif term_lower in table_lower:
                    score += 12
                elif term_lower in desc_lower:
                    score += 5

            # === RANKING FRAMEWORK BOOSTS ===
            # Boost for exact prefix matches on compound fields
            if any(name_lower.startswith(pk.lower()) for pk in primary_keywords):
                score += 20

            # Boost for underscore-separated exact word matches
            name_parts = name_lower.split('_')
            for pk in primary_keywords:
                if pk.lower() in name_parts:
                    score += 15

            # === PENALTIES FOR NEAR-MISSES ===
            # Penalize generic single-word matches without entity context
            if len(primary_keywords) == 1 and primary_matches == 1 and entity_boost == 0:
                penalties += 20
                logger.debug(f"Generic match penalty for {name_lower}")

            # Penalize if description match only (no name/table match)
            if score > 0 and score == sum([8 for term in primary_keywords if term.lower() in desc_lower]):
                penalties += 15

            final_score = max(0, score - penalties)

            if final_score > 0:
                logger.debug(f"Score {final_score} for {table_lower}.{name_lower} (base: {score}, penalties: {penalties})")

            return final_score

        # Score and filter fields using advanced scoring
        scored_fields = [(field, advanced_keyword_score(field)) for field in all_fields]
        scored_fields.sort(key=lambda x: x[1], reverse=True)

        # Log top scoring fields for debugging
        logger.info(f"Query: '{request.query}' | Total fields: {len(all_fields)}")
        logger.info(f"Top 10 scored fields:")
        for i, (field, score) in enumerate(scored_fields[:10]):
            logger.info(f"  {i+1}. Score {score}: {field.table_name}.{field.name}")

        # Take top 150 fields for AI analysis (increased from 100)
        top_fields = [f for f, s in scored_fields[:150] if s > 0]
        logger.info(f"Sending {len(top_fields)} fields to AI for analysis")

        # If no keyword matches, take fields from tables with relevant names
        if not top_fields:
            # Try to find tables with relevant names first
            relevant_tables = []
            query_lower = request.query.lower()
            for field in all_fields:
                table_lower = field.table_name.lower()
                for word in query_lower.split():
                    if len(word) > 3 and word in table_lower:
                        relevant_tables.append(field)
                        break

            if relevant_tables:
                top_fields = relevant_tables[:150]
            else:
                # Last resort: random sample
                import random
                top_fields = random.sample(all_fields, min(100, len(all_fields)))

        # Convert to dictionaries for AI processing with metadata
        fields_data = []
        for field in top_fields:
            # Calculate metadata confidence
            metadata_confidence = "unknown"
            if field.description and len(field.description) > 20:
                metadata_confidence = "high"
            elif field.description and len(field.description) > 5:
                metadata_confidence = "medium"
            else:
                metadata_confidence = "low"

            fields_data.append({
                'id': str(field.id),
                'name': field.name,
                'description': field.description or 'No description',
                'dataType': field.type,
                'tableName': field.table_name,
                'databaseName': field.database_name,
                'sourceName': field.source_name,
                'is_primary_key': field.is_primary_key or False,
                'is_nullable': field.nullable if field.nullable is not None else True,
                'metadata_confidence': metadata_confidence
            })

        # Use OpenAI to match fields to the query with limited dataset
        # Format: emphasize table name by putting it first
        fields_text = "\n".join([
            f"{i+1}. Table: {f['tableName']} | Field: {f['name']} | Type: {f['dataType']} | Description: {f['description'][:80]}"
            for i, f in enumerate(fields_data)
        ])

        matching_prompt = f"""You are a precision database field matching expert analyzing pre-scored candidates.

SEARCH INTENT:
Query: "{request.query}"
Core Concept: {core_concept}
Interpretation: {interpretation}

PRIMARY KEYWORDS (must match): {', '.join(primary_keywords)}
EXCLUSION TERMS (penalize if present alone): {', '.join(exclusion_keywords)}
PRIMARY ENTITIES (authoritative sources): {', '.join(primary_entities)}
SECONDARY ENTITIES (supporting context): {', '.join(secondary_entities)}

Pre-filtered candidate fields ({len(fields_data)} total - already scored for relevance):
{fields_text}

CRITICAL MATCHING RULES:
1. INTENT LOCK: Fields must match the CORE CONCEPT ({core_concept}), not just generic terms
2. ENTITY SCOPING: Strongly prefer fields from PRIMARY ENTITIES tables ({', '.join(primary_entities)})
3. COMPOUND MATCHING: Field+Table combinations (e.g., "Customer.EmploymentStatus") score higher than partial matches
4. EXCLUSION FILTER: Penalize fields containing exclusion terms unless primary keywords provide context
5. DISAMBIGUATION: Distinguish base entities from derived/secondary forms (e.g., primary customer vs co-applicant)

RANKING PRIORITIES (in order):
1. Exact match on core concept in primary entity table (Score: 0.95-1.0)
2. Field name contains core concept + primary entity table (Score: 0.85-0.94)
3. Multiple primary keywords in table.field combination (Score: 0.75-0.84)
4. Single primary keyword + primary entity context (Score: 0.65-0.74)
5. Related terms in primary entity context (Score: 0.50-0.64)
6. Weak matches in secondary entities (Score: 0.40-0.49)

PENALIZE:
- Fields with exclusion terms but no primary keyword context (-0.3 to score)
- Generic field names without entity scoping (-0.2 to score)
- Fields from unrelated entities or schemas (-0.2 to score)
- Description-only matches with no name relevance (-0.15 to score)

Return a JSON array with objects containing:
- "index": the field number (1-based)
- "score": precision-adjusted relevance score from 0.0 to 1.0
- "reason": explanation citing specific matches to core concept, keywords, and entity context (max 50 words)

Only include fields with score >= 0.5 (stricter threshold). Sort by score descending. Return top {min(request.limit, 15)} matches.

Example:
[
  {{"index": 12, "score": 0.98, "reason": "Customer.EmploymentStatus - exact core concept match in primary entity table"}},
  {{"index": 5, "score": 0.88, "reason": "Customer.EmploymentType - contains 'employment' primary keyword in Customer entity"}},
  {{"index": 23, "score": 0.72, "reason": "Employment.CustomerID - links employment data to customer entity"}}
]"""

        matching_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a database field matching expert. Analyze queries and match them to database fields based on semantic meaning and business context."},
                {"role": "user", "content": matching_prompt}
            ],
            max_tokens=2000,
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

        # Build result list with metadata
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
                    reason=match["reason"],
                    metadata_confidence=field_data['metadata_confidence'],
                    is_primary_key=field_data['is_primary_key'],
                    is_nullable=field_data['is_nullable']
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