import chromadb

# 1. Initialize a local database that saves data to a folder on your disk
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# 2. Create a storage segment (called a "collection") for our parts
# If it already exists, this will just load it
collection = chroma_client.get_or_create_collection(name="manufacturing_memory")

# 3. Add some historical reference data to the memory bank
print("Writing historical context to memory...")
collection.add(
    documents=[
        "Standard price for Nema 23 Stepper Motor is $45.00 from Vendor A.",
        "High-Torque Actuator model X-100 costs $250.00, shipped from Ohio.",
        "Bulk orders of Pneumatic Cylinders receive a 10% discount."
    ],
    ids=["id1", "id2", "id3"] # Every memory needs a unique hardware ID
)
print("Memory saved successfully!\n")

# 4. Perform a Semantic (Meaning-Based) Query
# Notice we are NOT using the exact words used above
query_text = "How much do we usually pay for motion control motors?"
print(f"Querying memory for: '{query_text}'")

results = collection.query(
    query_texts=[query_text],
    n_results=1 # Give us the single closest match
)

print("\n=== RETRIEVED MEMORY ===")
print(results['documents'][0][0])
print("=========================")