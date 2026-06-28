"""
OmniData Studio - Multi-Modal Ingestion Pipeline
This module handles unstructured data extraction. It leverages a Vision/Language
Model (Gemini) to parse PDF invoices, extract key financial entities into a strict 
JSON schema, and execute a dual-write pattern. Includes exponential backoff for API resilience.
"""

import os
import json
import time
import logging
from typing import Dict, Any
import pandas as pd
import chromadb
from PyPDF2 import PdfReader
from google import genai
from sqlalchemy import create_engine
from config import config

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client Initialization
# ---------------------------------------------------------------------------
try:
    gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    engine = create_engine(config.SUPABASE_URL)
    chroma_client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)
    memory_bank = chroma_client.get_or_create_collection(name="invoice_memory")
except Exception as e:
    logger.error(f"Initialization error in pipeline: {e}")

# ---------------------------------------------------------------------------
# Core Pipeline Functions
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        logger.error(f"PDF Extraction failed for {pdf_path}: {e}")
        raise

def parse_invoice_with_ai(raw_text: str) -> Dict[str, Any]:
    prompt = f"""
    Analyze the following invoice text and extract the exact values for: 
    - invoice_date
    - items_billed (as a list of items or a descriptive string)
    - total_amount
    
    Return STRICTLY as a valid JSON object. If total_amount contains a '$' or commas, include them.
    Do not include markdown formatting or explanations.
    
    Text: {raw_text}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            
            raw_json = response.text.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3].strip()
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:-3].strip()
                
            return json.loads(raw_json)
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s...
                    logger.warning(f"Gemini API busy (Attempt {attempt + 1}/{max_retries}). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
            logger.error(f"AI Parsing failed after {attempt + 1} attempts: {e}")
            return {}

def process_invoice(pdf_path: str) -> bool:
    filename = os.path.basename(pdf_path)
    logger.info(f"Initiating multi-modal pipeline for: {filename}")
    
    try:
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text:
            logger.warning(f"No text extracted from {filename}")
            return False
            
        data_dictionary = parse_invoice_with_ai(raw_text)
        if not data_dictionary:
            logger.error(f"Failed to parse entities from {filename}")
            return False

        flat_items_string = str(data_dictionary.get("items_billed", ""))
        raw_total = str(data_dictionary.get("total_amount", "0"))
        try:
            clean_total = float(raw_total.replace('$', '').replace(',', '').strip())
        except ValueError:
            clean_total = 0.0 
            
        raw_date = str(data_dictionary.get("invoice_date", "Unknown"))

        # 1. Deterministic Ledger
        invoice_df = pd.DataFrame([{
            "id": filename,
            "invoice_date": raw_date,
            "items_billed": flat_items_string,
            "total_amount": clean_total
        }])
        invoice_df.to_sql("invoices", engine, if_exists='append', index=False)
        logger.info(f"PostgreSQL Write Successful for {filename}")

        # 2. Semantic Vector Memory
        safe_metadata = {
            "source": filename,
            "invoice_date": raw_date,
            "total_amount": raw_total
        }
        memory_bank.add(
            documents=[raw_text],
            metadatas=[safe_metadata],
            ids=[filename]
        )
        logger.info(f"ChromaDB Vector Write Successful for {filename}")
        
        return True

    except Exception as e:
        logger.error(f"Pipeline failure for {filename}: {e}")
        return False