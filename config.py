import os
import logging
from dotenv import load_dotenv

# Initialize environment variables from .env file
load_dotenv()

class Config:
    """Central configuration class for OmniData Studio."""
    
    # AI Providers
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        logging.warning("GROQ_API_KEY is not set in the environment.")
        
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        logging.warning("GEMINI_API_KEY is not set in the environment.")

    # Database
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    if not SUPABASE_URL:
        logging.warning("SUPABASE_URL is not set. Database connections will fail.")

    # Application Settings
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./chroma_db")
    UPLOAD_DIRECTORY = os.getenv("UPLOAD_DIRECTORY", "./data_uploads")

# Instantiate a global configuration object
config = Config()