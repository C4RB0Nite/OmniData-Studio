"""
OmniData Studio - Core Agentic Routing and Execution Module
This module orchestrates a multi-agent cognitive architecture. It utilizes a lightweight
LLM for deterministic intent routing, a specialized Text-to-SQL agent with dynamic schema 
introspection, and a Semantic RAG agent for unstructured data querying.
"""

import logging
from typing import Dict, Any
import chromadb
from groq import Groq
from sqlalchemy import create_engine, text
from config import config

# Initialize professional logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client Initialization
# ---------------------------------------------------------------------------
try:
    groq_client = Groq(api_key=config.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")

try:
    engine = create_engine(config.SUPABASE_URL)
except Exception as e:
    logger.error(f"Failed to initialize Database engine: {e}")

try:
    chroma_client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)
    memory_bank = chroma_client.get_or_create_collection(name="invoice_memory")
except Exception as e:
    logger.error(f"Failed to initialize Vector Database: {e}")


# ---------------------------------------------------------------------------
# AGENT 1: The Cognitive Router
# ---------------------------------------------------------------------------
def classify_intent(user_query: str) -> str:
    """
    Acts as the semantic gatekeeper. Evaluates the user's natural language query
    and routes it deterministically to either the SQL execution path or the Vector RAG path.
    
    Args:
        user_query (str): The raw input from the user.
        
    Returns:
        str: Routing directive ('SQL' or 'VECTOR').
    """
    logger.info("Agent 1: Classifying user intent...")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are a deterministic router. If the user asks to calculate, sum, "
                        "count, sort, pull data, create tables, edit tables, or retrieve specific "
                        "financial numbers/tables, reply ONLY with the word 'SQL'. If the user asks "
                        "to read documents, search PDFs, extract semantic text, find specific names "
                        "in documents, or asks about general concepts, reply ONLY with the word 'VECTOR'."
                    )
                },
                {"role": "user", "content": user_query}
            ],
            temperature=0.0,
            max_tokens=10
        )
        return response.choices[0].message.content.strip().upper()
    except Exception as e:
        logger.error(f"Routing classification failed: {e}")
        return "SQL"  # Default fallback


# ---------------------------------------------------------------------------
# AGENT 2: The PostgreSQL Developer
# ---------------------------------------------------------------------------
def execute_sql_path(user_query: str) -> Dict[str, Any]:
    """
    Introspects the live PostgreSQL schema to inject exact data types into the LLM context.
    Translates natural language into strict, type-safe PostgreSQL syntax and executes it.
    
    Args:
        user_query (str): The natural language data request.
        
    Returns:
        Dict[str, Any]: Contains the generated SQL string and the database response/error.
    """
    logger.info("Agent 2: SQL intent detected. Introspecting database schema...")
    
    schema_info = ""
    try:
        # Dynamic Schema Introspection with Type Extraction
        with engine.connect() as conn:
            tables = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )).fetchall()
            
            for table in tables:
                table_name = table[0]
                cols = conn.execute(text(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';"
                )).fetchall()
                
                column_details = [f'"{col[0]}" ({col[1]})' for col in cols]
                schema_info += f"Table '{table_name}' with columns: {', '.join(column_details)}\n"
    except Exception as e:
        logger.error(f"Database introspection failed: {e}")

    # Universal PostgreSQL Prompt configuration
    system_prompt = f"""You are a Senior PostgreSQL Database Engineer. Based on this LIVE SCHEMA and its exact Data Types:
{schema_info}

Write a valid PostgreSQL query to answer the user's question. Return ONLY the raw SQL code. No markdown, no backticks, no explanations.
CRITICAL UNIVERSAL RULES:
1. ALWAYS wrap ALL column and table names in double quotes (e.g., "isOpen") to respect PostgreSQL case-sensitivity.
2. Ensure data types match when joining or inserting. Use the provided schema data types to determine if casting (::type) is necessary.
3. Postgres Math: The ROUND(value, decimals) function requires a NUMERIC type. ALWAYS cast floats/double precision to numeric before rounding (e.g., ROUND((a/b)::numeric, 2)).
4. Postgres Dates: Standard date strings (like '2019-12-30 00:00:00') can be cast directly with ::timestamp. Compact integers (like 20200125) must be cast to text, then parsed: TO_DATE("col"::text, 'YYYYMMDD').
5. NEVER query system catalogs (pg_catalog, information_schema). Focus only on the public data tables provided above."""

    try:
        logger.info("Agent 2: Generating PostgreSQL execution code...")
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.1
        )
        
        # Clean the returned SQL string
        sql_code = response.choices[0].message.content.strip()
        sql_code = sql_code.replace("```sql", "").replace("```", "").strip() 
        
        # Execute the generated SQL safely using transaction context
        with engine.begin() as conn:
            result = conn.execute(text(sql_code))
            
            if result.returns_rows:
                rows = result.fetchall()
                str_result = [str(row) for row in rows]
                display_answer = f"Database Result: {str_result[:5]}... (Truncated for display)" if str_result else "No data found."
            else:
                display_answer = "Database structure updated successfully. No rows returned."
        
        return {
            "answer": display_answer, 
            "sql": sql_code
        }
    except Exception as e:
        logger.error(f"PostgreSQL Execution Failed: {e}")
        return {"answer": f"Execution Error: {str(e)}", "sql": "SELECT 'ERROR';"}


# ---------------------------------------------------------------------------
# AGENT 3: The Semantic Analyst (RAG)
# ---------------------------------------------------------------------------
def execute_semantic_path(user_query: str) -> str:
    """
    Handles unstructured data queries. Embeds the user query, searches the ChromaDB vector 
    space for relevant document chunks, and utilizes context-augmented generation to answer.
    
    Args:
        user_query (str): The conceptual or document-based query.
        
    Returns:
        str: The contextualized natural language response.
    """
    logger.info("Agent 3: Semantic intent detected. Fetching vector context...")
    
    try:
        results = memory_bank.query(query_texts=[user_query], n_results=2)
        
        if results['documents'] and len(results['documents'][0]) > 0:
            retrieved_context = "\n".join(results['documents'][0])
        else:
            retrieved_context = "No relevant historical context found in the knowledge base."
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        f"You are a helpful analyst. Answer the user's question based strictly on "
                        f"this retrieved context:\n{retrieved_context}\nIf the answer is not in "
                        f"the context, explicitly state that you do not have the data to answer."
                    )
                },
                {"role": "user", "content": user_query}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Semantic Search Failed: {e}")
        return f"Semantic Retrieval Error: {str(e)}"