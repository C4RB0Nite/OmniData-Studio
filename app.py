import os
import json
from PyPDF2 import PdfReader
from google import genai
from google.genai import types
import chromadb

# ==========================================
# SETUP & CONFIGURATION
# ==========================================
API_KEY = "YOUR_API_KEY_HERE"
client = genai.Client(api_key=API_KEY)

# Initialize the Vector Memory Bank
print("Spinning up Semantic Memory...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
memory_bank = chroma_client.get_or_create_collection(name="invoice_memory")

# ==========================================
# STEP A: EXTRACT RAW TEXT FROM PDF
# ==========================================
def extract_text_from_pdf(pdf_path):
    print("Reading PDF file...")
    reader = PdfReader(pdf_path)
    raw_text = ""
    for page in reader.pages:
        raw_text += page.extract_text()
    return raw_text

# ==========================================
# STEP B: ASK AI FOR STRUCTURED JSON
# ==========================================
def parse_invoice_with_ai(raw_text):
    print("Sending text to the AI (Requesting JSON format)...")
    
    prompt = f"""
    Extract the following information from the invoice:
    - invoice_date
    - items_billed (a short summary of the part numbers/services)
    - total_amount

    Return the data STRICTLY as a JSON object using the exact keys listed above.
    
    Invoice text:
    {raw_text}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text

# ==========================================
# STEP C: ENCODE INTO SEMANTIC MEMORY
# ==========================================
def save_to_memory(data_dictionary, filename):
    print(f"Encoding {filename} into Vector Memory...")
    
    # 1. Create a descriptive sentence for the database to mathematically embed
    date = data_dictionary.get("invoice_date", "Unknown Date")
    items = data_dictionary.get("items_billed", "Unknown Items")
    total = data_dictionary.get("total_amount", "$0.00")
    
    memory_string = f"Invoice {filename} billed on {date} for: {items}. The total cost was {total}."
    
    # 2. Store it in ChromaDB
    memory_bank.add(
        documents=[memory_string],
        metadatas=[data_dictionary], # We can hide the raw JSON in the background metadata!
        ids=[filename]               # Use the filename as the unique system ID
    )
    print("Memory encoded and stored!")

# ==========================================
# MAIN EXECUTION FLOW
# ==========================================
if __name__ == "__main__":
    invoice_folder = "invoices"
    
    if not os.path.exists(invoice_folder):
        print(f"Error: Please create '{invoice_folder}' and add PDFs.")
    else:
        print(f"\n--- INITIATING BATCH INGESTION ---")
        
        for filename in os.listdir(invoice_folder):
            if filename.endswith(".pdf"):
                print(f"\nProcessing: {filename}")
                full_path = os.path.join(invoice_folder, filename)
                
                try:
                    extracted_data = extract_text_from_pdf(full_path)
                    ai_json_string = parse_invoice_with_ai(extracted_data)
                    ai_data_dict = json.loads(ai_json_string)
                    
                    # Route the data to the memory bank instead of the CSV
                    save_to_memory(ai_data_dict, filename)
                    
                except Exception as e:
                    print(f"FAILED on {filename}: {e}")
        
        print("\n*** BATCH INGESTION & ENCODING COMPLETE ***")