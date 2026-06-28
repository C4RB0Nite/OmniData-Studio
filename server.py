"""
OmniData Studio - Core API Gateway (Resilience Edition)
Manages system endpoints, UI/UX synchronizations, and routes OS-level activities
into the Unified Event Stream memory. Features Graceful Degradation to survive 
aggressive Windows OS Application Control blocks on compiled C-extensions.
"""

import os
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from config import config
from smart_agent import process_cognitive_request, log_os_event
from pipeline import process_invoice

# Initialize professional logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resilience Interceptor: Graceful Degradation for strict Windows environments
# ---------------------------------------------------------------------------
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError as e:
    logger.critical("⚠️ OS SECURITY BLOCK DETECTED ⚠️")
    logger.critical(f"Error: {e}")
    logger.critical("Windows Application Control is actively blocking NumPy/Pandas C-extensions (.dll/.pyd).")
    logger.critical("The Gateway will boot in 'Degraded Mode'. AI routing is active, but raw SQL visualization and CSV imports are disabled.")
    PANDAS_AVAILABLE = False
    pd = None

# Initialize FastAPI App
app = FastAPI(title="OmniData Studio API", version="2.0.1 (Resilience Edition)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    engine = create_engine(config.SUPABASE_URL)
except Exception as e:
    logger.error(f"Database Engine failed to initialize: {e}")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = []

class QueryRequest(BaseModel):
    sql: str

@app.get("/api/schema")
async def get_database_schema() -> Dict[str, Any]:
    try:
        schema_tree = []
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")).fetchall()
            for table in tables:
                schema_tree.append({"table_name": table[0]})
        return {"status": "success", "schema": schema_tree}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> Dict[str, Any]:
    try:
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]
        return process_cognitive_request(request.query, history_dicts)
    except Exception as e:
        return {"status": "error", "response": str(e)}

@app.post("/api/query")
async def execute_custom_query(request: QueryRequest) -> Dict[str, Any]:
    if not PANDAS_AVAILABLE:
        return {"status": "error", "message": "SQL Data Grid disabled: Windows Application Control is blocking Pandas."}
        
    try:
        # Intercept manual queries and push them to procedural memory
        log_os_event("Manual User SQL Execution", request.sql)
        
        df = pd.read_sql_query(request.sql, engine)
        df = df.fillna("").astype(str)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ledger")
async def get_ledger() -> Dict[str, Any]:
    if not PANDAS_AVAILABLE:
        return {"status": "error", "data": []}
        
    try:
        df = pd.read_sql_query("SELECT * FROM invoices ORDER BY total_amount DESC LIMIT 50", engine)
        df = df.fillna("").astype(str)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "data": []}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        os.makedirs(config.UPLOAD_DIRECTORY, exist_ok=True)
        file_path = os.path.join(config.UPLOAD_DIRECTORY, file.filename)
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        log_os_event("Data Ingestion", f"Uploaded file: {file.filename}")

        if file.filename.lower().endswith(".csv"):
            if not PANDAS_AVAILABLE:
                raise HTTPException(status_code=500, detail="CSV upload disabled: Windows is blocking Pandas.")
                
            df = pd.read_csv(file_path)
            table_name = os.path.splitext(file.filename)[0]
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            return {"status": "success", "message": f"CSV {file.filename} processed."}

        elif file.filename.lower().endswith(".pdf"):
            success = process_invoice(file_path)
            if success:
                return {"status": "success", "message": f"PDF {file.filename} parsed and ingested."}
            else:
                raise HTTPException(status_code=500, detail="AI PDF processing failed.")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format.")
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)