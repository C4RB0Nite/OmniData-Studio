"""
OmniData Studio - Multi-Modal Ingestion Pipeline
This module handles unstructured data extraction. It leverages a Vision/Language
Model (Gemini) to parse PDF invoices, extract key financial entities into a strict 
JSON schema, and execute a dual-write pattern: structural data to PostgreSQL and 
semantic data to ChromaDB for RAG context.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import pandas as pd
import chromadb
from PyPDF2 import PdfReader
from google import genai
from sqlalchemy import create_engine

from config import config

# Initialize professional logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client Initialization
# ---------------------------------------------------------------------------
try:
    gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini Client: {e}")

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
# Core Pipeline Functions
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts raw string text from a given PDF file.
    
    Args:
        pdf_path (str): The absolute or relative path to the PDF file.
        
    Returns:
        str: The complete extracted text.
    """
    try:
        reader = PdfReader(pdf_path)
        return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        logger.error(f"PDF Extraction failed for {pdf_path}: {e}")
        raise


def parse_invoice_with_ai(raw_text: str) -> Dict[str, Any]:
    """
    Passes raw invoice text to the LLM to extract structured entities.
    Enforces a strict JSON output schema.
    
    Args:
        raw_text (str): The unstructured text from the PDF.
        
    Returns:
        Dict[str, Any]: A parsed dictionary containing invoice_date, items_billed, and total_amount.
    """
    prompt = f"""
    Analyze the following invoice text and extract the exact values for: 
    - invoice_date
    - items_billed (as a list of items or a descriptive string)
    - total_amount
    
    Return STRICTLY as a valid JSON object. If total_amount contains a '$' or commas, include them.
    Do not include markdown formatting or explanations.
    
    Text: {raw_text}
    """
    
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        # Clean potential markdown formatting from LLM response
        raw_json = response.text.strip()
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:-3].strip()
        elif raw_json.startswith("```"):
            raw_json = raw_json[3:-3].strip()
            
        return json.loads(raw_json)
    except Exception as e:
        logger.error(f"AI Parsing failed: {e}")
        return {}


def process_invoice(pdf_path: str) -> bool:
    """
    The main orchestration function for PDF ingestion. Executes the extraction,
    AI parsing, and the dual-write to PostgreSQL and ChromaDB.
    
    Args:
        pdf_path (str): The file path to the uploaded PDF.
        
    Returns:
        bool: True if ingestion was successful, False otherwise.
    """
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

        # Data Sanitization
        flat_items_string = str(data_dictionary.get("items_billed", ""))
        raw_total = str(data_dictionary.get("total_amount", "0"))
        try:
            clean_total = float(raw_total.replace('$', '').replace(',', '').strip())
        except ValueError:
            clean_total = 0.0 
            
        raw_date = str(data_dictionary.get("invoice_date", "Unknown"))

        # 1. Write to PostgreSQL (Deterministic Ledger)
        invoice_df = pd.DataFrame([{
            "id": filename,
            "invoice_date": raw_date,
            "items_billed": flat_items_string,
            "total_amount": clean_total
        }])
        invoice_df.to_sql("invoices", engine, if_exists='append', index=False)
        logger.info(f"PostgreSQL Write Successful for {filename}")

        # 2. Write to ChromaDB (Semantic Vector Memory)
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