"""
OmniData Studio - Core API Gateway
This module serves as the primary FastAPI backend. It manages CORS configurations,
provides schema introspection endpoints for the React frontend, orchestrates file 
uploads (routing to either Pandas or AI pipelines), and serves as the bridge to 
the cognitive routing agents.
"""

import os
import logging
from typing import Dict, Any
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from config import config
from smart_agent import classify_intent, execute_sql_path, execute_semantic_path
from pipeline import process_invoice  # Importing the ingestion pipeline

# Initialize professional logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="OmniData Studio API",
    description="Agentic Data Operating System Backend",
    version="1.0.0"
)

# CORS Middleware (Allows Next.js frontend to communicate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database Engine securely
try:
    engine = create_engine(config.SUPABASE_URL)
except Exception as e:
    logger.error(f"Database Engine failed to initialize: {e}")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    query: str

class QueryRequest(BaseModel):
    sql: str


# ---------------------------------------------------------------------------
# Cloud PostgreSQL Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/schema")
async def get_database_schema() -> Dict[str, Any]:
    """
    Introspects the Supabase PostgreSQL database and returns the schema tree.
    This dynamically populates the Left Sidebar in the React UI.
    """
    try:
        schema_tree = []
        with engine.connect() as conn:
            tables = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )).fetchall()
            
            for table in tables:
                schema_tree.append({"table_name": table[0]})
                
        return {"status": "success", "schema": schema_tree}
    except Exception as e:
        logger.error(f"Schema Fetch Error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> Dict[str, Any]:
    """
    The primary cognitive endpoint. Receives natural language from the Copilot,
    classifies the intent, and routes to the appropriate agentic execution path.
    """
    try:
        # Agent 1: Router
        route = classify_intent(request.query)
        logger.info(f"Query routed to: {route}")

        if route == "SQL":
            # Agent 2: Text-to-SQL
            data = execute_sql_path(request.query)
            return {
                "status": "success", 
                "response": data["answer"], 
                "route": route, 
                "sql": data.get("sql")
            }
        else:
            # Agent 3: Vector RAG
            answer = execute_semantic_path(request.query)
            return {
                "status": "success", 
                "response": answer, 
                "route": route, 
                "sql": None
            }
    except Exception as e:
        logger.error(f"Chat Endpoint Error: {e}")
        return {"status": "error", "response": str(e)}


@app.post("/api/query")
async def execute_custom_query(request: QueryRequest) -> Dict[str, Any]:
    """
    Executes raw SQL on the Supabase database. Triggered by UI clicks or AI output.
    """
    try:
        df = pd.read_sql_query(request.sql, engine)
        df = df.fillna("").astype(str)  # Sanitize for JSON serialization
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"SQL Query Execution Error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/ledger")
async def get_ledger() -> Dict[str, Any]:
    """Returns the default invoice data for the center workspace initialization."""
    try:
        df = pd.read_sql_query("SELECT * FROM invoices ORDER BY total_amount DESC LIMIT 50", engine)
        df = df.fillna("").astype(str)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        logger.error(f"Ledger Fetch Error: {e}")
        return {"status": "error", "data": []}


# ---------------------------------------------------------------------------
# Universal Data Ingestion Endpoint
# ---------------------------------------------------------------------------
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Universal ingestion endpoint. Evaluates the file type and routes it to 
    the appropriate data pipeline (Pandas for CSV, AI Pipeline for PDF).
    """
    try:
        os.makedirs(config.UPLOAD_DIRECTORY, exist_ok=True)
        file_path = os.path.join(config.UPLOAD_DIRECTORY, file.filename)
        
        # Save file locally
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        logger.info(f"File saved to staging: {file.filename}")

        # Route 1: Deterministic Tabular Pipeline
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
            table_name = os.path.splitext(file.filename)[0] # e.g. "dataset"
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            logger.info(f"CSV Ingestion complete. Table created: {table_name}")
            return {"status": "success", "message": f"CSV {file.filename} processed."}

        # Route 2: Multi-Modal AI Pipeline
        elif file.filename.lower().endswith(".pdf"):
            success = process_invoice(file_path)
            if success:
                return {"status": "success", "message": f"PDF {file.filename} parsed and ingested."}
            else:
                raise HTTPException(status_code=500, detail="AI PDF processing failed.")

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or PDF.")

    except Exception as e:
        logger.error(f"Upload Endpoint Error: {e}")
        return {"status": "error", "message": str(e)}
    
if __name__ == "__main__":
    import uvicorn
    logger.info("Booting FastAPI OmniData Gateway on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)