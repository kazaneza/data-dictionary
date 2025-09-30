"""
AI-powered description generation (context-driven, vendor-agnostic, JSON-safe)

- No hard-coded vendors or domains.
- Uses ONLY your provided variables:
  source_name, source_description, database_name, database_description, table_name, fields
- Sanitizes incoming metadata (won't feed "business data"/old descriptions to the model).
- Extracts context vocabulary from the provided variables & field names.
- Prompts the model with those context words; forbids generic filler.
- Forces JSON outputs and retries once if parsing fails; also extracts JSON from code fences.
- Rewrites common tokens purely by token detection (e.g., XMLTYPE -> "Structured details …", LCY/FCY).
- Cleans filler words and enforces concise length caps.
- Optional manual overrides; optional in-memory caching by schema hash.

Keep your existing:
  - TableField model (fieldName, dataType, isPrimaryKey, isForeignKey, isNullable, defaultValue?)
  - BankingIntelligence fallbacks
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from .models import TableField
from .banking_intelligence import BankingIntelligence

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

load_dotenv()
logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TABLE_DESC_LIMIT = int(os.getenv("TABLE_DESC_LIMIT", "160"))
FIELD_DESC_LIMIT = int(os.getenv("FIELD_DESC_LIMIT", "90"))

JSON_STRICT_RETRY = int(os.getenv("JSON_STRICT_RETRY", "1"))
ENABLE_CACHE = os.getenv("AI_DESC_CACHE", "1") not in {"0", "false", "False"}

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Words/phrases to ban in prompts/outputs
FORBIDDEN_PHRASES = {
    "business data", "data field", "information", "business information",
    "data details", "business details", "info"
}

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _tokens_from_text(*values: Optional[str], max_tokens: int = 40) -> List[str]:
    """Extract meaningful tokens from provided context strings (no vendors hard-coded)."""
    text = " ".join([v for v in values if v])[:5000]  # cap to keep prompts lean
    # split by non-alnum, keep uppercase tokens and camel/snake parts
    raw = re.split(r"[^A-Za-z0-9_]+", text)
    parts = []
    for w in raw:
        if not w:
            continue
        # split camelCase / PascalCase
        camel_parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+", w)
        if len(camel_parts) > 1:
            parts.extend(camel_parts)
        else:
            parts.append(w)
    # normalize, remove tiny tokens (but keep numbers)
    norm = []
    for p in parts:
        if p.isdigit():
            norm.append(p)
        else:
            p2 = p.strip("_").strip()
            if len(p2) >= 3:
                norm.append(p2)
    # de-dup while preserving order
    seen, out = set(), []
    for t in norm:
        tl = t
        if tl.lower() in seen:
            continue
        seen.add(tl.lower())
        out.append(t)
        if len(out) >= max_tokens:
            break
    return out

def _sanitize_fields_for_prompt(fields: List[TableField]) -> str:
    """
    Build a field list for the prompt WITHOUT carrying over any existing descriptions.
    Only pass name, type, and flags (PK/FK/Required). This avoids "business data" echoes.
    """
    rows = []
    for f in fields:
        line = f"- {f.fieldName} ({f.dataType})"
        flags = []
        if f.isPrimaryKey == "Yes": flags.append("PK")
        if f.isForeignKey == "Yes": flags.append("FK")
        if f.isNullable == "NO":    flags.append("Required")
        if flags:
            line += f" [{', '.join(flags)}]"
        rows.append(line)
    return "\n".join(rows)

def _extract_json_loose(text: str) -> Optional[dict]:
    """If JSON parsing fails, try to extract the first {...} block (handles code fences)."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    candidate = m.group(0)
    try:
        return json.loads(candidate)
    except Exception:
        return None

def _ask_json(prompt: str, max_tokens: int, retries: int = JSON_STRICT_RETRY) -> dict:
    """Ask model for JSON; retry with stricter reminder; attempt loose extraction."""
    raw = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens,
    ).choices[0].message.content

    try:
        return json.loads(raw)
    except Exception:
        loose = _extract_json_loose(raw)
        if loose is not None:
            return loose

    for _ in range(max(0, retries)):
        strict = prompt + "\n\nREMINDER: Output JSON ONLY. No prose, no code fences."
        raw2 = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": strict}],
            temperature=0.1,
            max_tokens=max_tokens,
        ).choices[0].message.content
        try:
            return json.loads(raw2)
        except Exception:
            loose = _extract_json_loose(raw2)
            if loose is not None:
                return loose

    raise ValueError("Model did not return valid JSON.")

def _clean_text(text: str, limit: int) -> str:
    """Trim filler words, tidy whitespace/punctuation, enforce length cap."""
    t = (text or "").strip().strip('"').strip("'")
    for bad in FORBIDDEN_PHRASES:
        t = re.sub(rf"\b{re.escape(bad)}\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).rstrip(".").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit - 1]
    cut = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return cut + "…"

def _is_bad(text: str) -> bool:
    """Simple QA: reject if too short or contains forbidden words."""
    if not text or len(text.strip()) < 15:
        return True
    lower = text.lower()
    if any(bad in lower for bad in FORBIDDEN_PHRASES):
        return True
    return False

def _schema_hash(table_name: str, fields: List[TableField]) -> str:
    payload = table_name + "|" + "|".join(
        f"{f.fieldName}:{f.dataType}:{f.isPrimaryKey}:{f.isForeignKey}:{f.isNullable}"
        for f in sorted(fields, key=lambda x: x.fieldName.lower())
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()

# -----------------------------------------------------------------------------
# Token-based rewrite (no vendor names; just expand common tokens if present)
# -----------------------------------------------------------------------------

TOKEN_HINTS = {
    "XMLTYPE": "Structured details (repeating elements)",
    "BOOKING_DATE": "Booking date (YYYYMMDD)",
    "VALUE_DATE": "Value date (YYYYMMDD)",
    "AMOUNT_LCY": "Amount in local currency",
    "AMOUNT_FCY": "Amount in foreign currency",
    "AMOUNT_DEAL_CCY": "Amount in deal currency",
    "DEAL_CCY": "Deal currency code",
    "EXCHANGE_RATE": "Exchange rate used",
    "DEAL_EXCH_RATE": "Exchange rate agreed at deal time",
    "TAX_EXCH_RATE": "Exchange rate used for tax",
    "ORIGINAL_AMOUNT": "Original amount before conversion",
    "ORIGINAL_CCY": "Original transaction currency",
    "ORIG_AMOUNT_LCY": "Original amount in local currency",
    "ORIG_LOCAL_EQUIV": "Original amount converted to local currency",
    "NARRATIVE": "Statement narrative",
    "MASK_NARRATIVE": "Narrative masked for display",
    "RECID": "Immutable record ID",
    "STMT_ENTRY_ID": "Statement entry ID",
    "STMT_NO": "Statement number/sequence",
    "REVERSAL_MARKER": "Reversal indicator/link",
    "RECORD_STATUS": "Entry status",
    "ACCOUNT_NUMBER": "Account number",
}

def _rewrite_tokens(text: str, field_name: Optional[str] = None) -> str:
    """Map known tokens (if present) to human phrasing. No vendor mentions."""
    t = text or ""
    # If we know the field name, prefer the field-based expansion
    key = (field_name or "").upper()
    if key in TOKEN_HINTS:
        # if the model returned something generic, replace entirely
        if len(t.strip()) < 10 or any(b in t.lower() for b in FORBIDDEN_PHRASES):
            return TOKEN_HINTS[key]
    # otherwise replace token occurrences inside the text
    for token, friendly in TOKEN_HINTS.items():
        if re.search(rf"\b{re.escape(token)}\b", t, re.IGNORECASE):
            t = re.sub(rf"\b{re.escape(token)}\b", friendly, t, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", t).strip()

# -----------------------------------------------------------------------------
# Manual overrides (optional; can load from YAML/DB later)
# -----------------------------------------------------------------------------

MANUAL_OVERRIDES: Dict[str, Dict[str, str]] = {
    # "TABLE_NAME": {
    #   "__table__": "Custom table description",
    #   "FIELD_NAME": "Custom field meaning"
    # }
}

# -----------------------------------------------------------------------------
# Caches
# -----------------------------------------------------------------------------

_CACHE_TABLE: Dict[str, str] = {}
_CACHE_FIELDS: Dict[str, Dict[str, str]] = {}

# -----------------------------------------------------------------------------
# Generator
# -----------------------------------------------------------------------------

class AIDescriptionGenerator:
    """Generates AI-powered descriptions (context-driven, vendor-agnostic)."""

    @staticmethod
    def generate_table_description(
        table_name: str,
        fields: List[TableField],
        source_name: Optional[str] = None,
        source_description: Optional[str] = None,
        database_name: Optional[str] = None,
        database_description: Optional[str] = None,
    ) -> str:
        try:
            # Cache by schema
            schema_key = _schema_hash(table_name, fields)
            if ENABLE_CACHE and schema_key in _CACHE_TABLE:
                return _CACHE_TABLE[schema_key]

            # Manual override
            ovr = MANUAL_OVERRIDES.get(table_name, {}).get("__table__")
            if ovr:
                desc = _clean_text(_rewrite_tokens(ovr), TABLE_DESC_LIMIT)
                if _is_bad(desc):
                    desc = BankingIntelligence.get_enhanced_table_fallback(table_name, source_name, fields)
                if ENABLE_CACHE:
                    _CACHE_TABLE[schema_key] = desc
                return desc

            # Build sanitized field context
            field_list = _sanitize_fields_for_prompt(fields)

            # Build context vocabulary dynamically from provided variables
            vocab = _tokens_from_text(
                source_name, source_description, database_name, database_description, table_name
            )
            # also include some prominent field tokens (UPPER words, e.g., LCY/FCY/MTI/STAN if present)
            field_tokens = _tokens_from_text(" ".join(f.fieldName for f in fields), max_tokens=20)
            vocab = (vocab + field_tokens)[:40]

            # Few-shot is generic (no vendor mention)
            fewshot = (
                'Example output: {"description": '
                '"Concise business summary of what this table stores and why it exists, '
                'using terms from the provided context."}'
            )

            prompt = f"""
You write SHORT BUSINESS descriptions for data tables using ONLY the provided context terms.
Do NOT invent vendor/product names. Prefer terms found in the context below.

Context:
- Source Name: {source_name or ""}
- Source Description: {source_description or ""}
- Database Name: {database_name or ""}
- Database Description: {database_description or ""}
- Table Name: {table_name}

Prefer these context words if relevant: {", ".join(vocab) if vocab else "(none)"}

Fields (name, type, flags):
{field_list}

Rules:
- Explain the BUSINESS purpose of the table (what it stores and why).
- Be specific; avoid filler like "business data", "information", "data field".
- ≤ {TABLE_DESC_LIMIT} characters.
- Output JSON only: {{"description": "..."}}.
{fewshot}
""".strip()

            data = _ask_json(prompt, max_tokens=max(220, TABLE_DESC_LIMIT + 100))
            desc = (data.get("description") or "").strip()
            desc = _rewrite_tokens(desc)          # token expansions if present
            desc = _clean_text(desc, TABLE_DESC_LIMIT)

            if _is_bad(desc):
                desc = BankingIntelligence.get_enhanced_table_fallback(table_name, source_name, fields)

            if ENABLE_CACHE:
                _CACHE_TABLE[schema_key] = desc

            logger.info(f"Generated AI table description for {table_name}: {desc}")
            return desc

        except Exception as e:
            logger.error(f"Error generating AI table description: {e}")
            return BankingIntelligence.get_enhanced_table_fallback(table_name, source_name, fields)

    @staticmethod
    def generate_field_descriptions(
        table_name: str,
        fields: List[TableField],
        source_name: Optional[str] = None,
        source_description: Optional[str] = None,
        database_name: Optional[str] = None,
        database_description: Optional[str] = None,
    ) -> List[TableField]:
        try:
            # Cache by schema
            schema_key = _schema_hash(table_name, fields)
            if ENABLE_CACHE and schema_key in _CACHE_FIELDS:
                mapping = _CACHE_FIELDS[schema_key]
                for f in fields:
                    f.description = mapping.get(f.fieldName) or f.description
                return fields

            # Manual overrides
            table_overrides = MANUAL_OVERRIDES.get(table_name, {})

            fields_context = _sanitize_fields_for_prompt(fields)

            vocab = _tokens_from_text(
                source_name, source_description, database_name, database_description, table_name
            )
            field_tokens = _tokens_from_text(" ".join(f.fieldName for f in fields), max_tokens=20)
            vocab = (vocab + field_tokens)[:40]

            fewshot_fields = (
                'Example output: {"ID": "Unique identifier", "CREATED_DATE": "Creation date (YYYYMMDD)"}'
            )

            prompt = f"""
You write SHORT BUSINESS meanings for each field using ONLY the provided context terms.
Do NOT invent vendor/product names. Prefer terms found in the context below.

Context:
- Source Name: {source_name or ""}
- Source Description: {source_description or ""}
- Database Name: {database_name or ""}
- Database Description: {database_description or ""}
- Table Name: {table_name}
Prefer these context words if relevant: {", ".join(vocab) if vocab else "(none)"}

Fields (name, type, flags):
{fields_context}

Rules:
- Provide one short BUSINESS meaning per field (how an analyst/user would read it).
- ≤ {FIELD_DESC_LIMIT} characters per field.
- Avoid filler like "business data", "information", "data field".
- Output ONE JSON object only: {{ "FIELD_NAME": "meaning", ... }}.
{fewshot_fields}
""".strip()

            data = _ask_json(prompt, max_tokens=max(2600, FIELD_DESC_LIMIT * 20))

            result_map: Dict[str, str] = {}
            for f in fields:
                # manual override first
                desc = table_overrides.get(f.fieldName)
                if not desc:
                    desc = data.get(f.fieldName, "") if isinstance(data, dict) else ""

                if not desc:
                    desc = BankingIntelligence.get_enhanced_field_fallback(
                        f.fieldName, f.dataType, source_name, table_name
                    )

                # token-based rewrite + cleanup
                desc = _rewrite_tokens(desc, field_name=f.fieldName)
                desc = _clean_text(desc, FIELD_DESC_LIMIT)
                if _is_bad(desc):
                    desc = BankingIntelligence.get_enhanced_field_fallback(
                        f.fieldName, f.dataType, source_name, table_name
                    )
                    desc = _clean_text(desc, FIELD_DESC_LIMIT)

                f.description = desc
                result_map[f.fieldName] = desc

            if ENABLE_CACHE:
                _CACHE_FIELDS[schema_key] = result_map

            logger.info(f"Generated AI field descriptions for {len(fields)} fields in table {table_name}")
            return fields

        except Exception as e:
            logger.error(f"Error generating AI field descriptions: {e}")
            for f in fields:
                f.description = BankingIntelligence.get_enhanced_field_fallback(
                    f.fieldName, f.dataType, source_name, table_name
                )
                f.description = _clean_text(f.description, FIELD_DESC_LIMIT)
            return fields
