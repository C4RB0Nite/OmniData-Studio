import os
import json
import csv
from PyPDF2 import PdfReader
from google import genai
from google.genai import types

# API Setup (Using Gemini-2.5-flash for better structured output). 

API_KEY = "YOUR_API_KEY_HERE"
client = genai.Client(api_key=API_KEY)

# Defiining a function to extract text from PDF using PyPDF2.
# This function reads the PDF file, iterates through each page, and concatenates the extracted text into a single string.

def extract_text_from_pdf(pdf_path):
    print("Reading PDF file...")
    reader = PdfReader(pdf_path)
    raw_text = ""
    for page in reader.pages:
        raw_text += page.extract_text()
    return raw_text

# Setting up a function to parse the extracted text with the AI, requesting a JSON response.
# This function sends a prompt to the Gemini model, asking it to extract specific fields from the invoice text and return them in a structured format.

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
    
    # The config parameter allows us to specify that we want the response in JSON format, which makes it easier to parse later on.
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text

# Saving the extracted and parsed data to a CSV file. We will append to the file if it already exists, and write headers only if it's a new file.
# This way, we can keep a growing database of invoices without losing previous entries.

def save_to_csv(data_dictionary, csv_filename):
    print(f"Saving data to {csv_filename}...")
    
    # Check if the file already exists so we know if we need to write the header row
    file_exists = os.path.isfile(csv_filename)
    
    # Open the CSV file in 'append' mode ('a') so we don't overwrite previous invoices
    with open(csv_filename, mode='a', newline='') as file:
        headers = ["invoice_date", "items_billed", "total_amount"]
        writer = csv.DictWriter(file, fieldnames=headers)
        
        if not file_exists:
            writer.writeheader()  # Write column names the very first time
            
        writer.writerow(data_dictionary) # Write the actual data
    
    print("Save complete!")


# Main execution block: This is where we define the folder to scan, check for its existence, and loop through each PDF file to process it.
# We also include error handling to ensure that one failed file doesn't stop the entire batch.

if __name__ == "__main__":
    # 1. Define the folder where our documents live
    invoice_folder = "invoices"
    database_file = "database.csv"
    
    # 2. Safety check: Does the folder exist?
    if not os.path.exists(invoice_folder):
        print(f"Error: Please create a folder named '{invoice_folder}' and add PDFs.")
    else:
        print(f"Scanning '{invoice_folder}' directory for invoices...\n")
        
        # 3. Loop through every file in the folder
        for filename in os.listdir(invoice_folder):
            
            # Only process PDF files
            if filename.endswith(".pdf"):
                print(f"--- Processing {filename} ---")
                
                # Create the full system path (e.g., "invoices/invoice_2.pdf")
                full_path = os.path.join(invoice_folder, filename)
                
                # Run the pipeline with basic error handling
                try:
                    extracted_data = extract_text_from_pdf(full_path)
                    ai_json_string = parse_invoice_with_ai(extracted_data)
                    ai_data_dict = json.loads(ai_json_string)
                    save_to_csv(ai_data_dict, database_file)
                    print(f"SUCCESS: Logged {filename} to database.\n")
                except Exception as e:
                    print(f"FAILED on {filename}: {e}\n")
        
        print("*** BATCH PROCESSING COMPLETE ***")