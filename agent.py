import chromadb
from google import genai

# ==========================================
# SETUP & CONFIGURATION
# ==========================================
API_KEY = "YOUR_API_KEY_HERE"
client = genai.Client(api_key=API_KEY)

# Connect to the existing local memory bank
print("Booting up Central Reasoning Engine...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Notice we use 'get_collection' here, because the memory must already exist
memory_bank = chroma_client.get_collection(name="invoice_memory")

# ==========================================
# COGNITIVE LOOP: RETRIEVE & REASON
# ==========================================
def ask_agent(user_question):
    # 1. The Hindbrain: Query the Vector Database for context
    print("\n[System] Searching vector memory for related context...")
    
    # We ask the DB for the top 2 closest mathematical matches to the question
    results = memory_bank.query(
        query_texts=[user_question],
        n_results=2 
    )
    
    # Extract the retrieved sentences from the database output
    retrieved_context = "\n".join(results['documents'][0])
    print(f"[System] Recalled Memory:\n{retrieved_context}")

    # 2. The Cortex: Send the memory and the question to the AI for analysis
    print("\n[System] Routing memory to the AI for analysis...")
    prompt = f"""
    You are a highly capable AI financial analyst agent. 
    Use the following retrieved historical data to answer the user's question. 
    If the answer is not in the historical data, say you do not know based on current records.
    Keep your answer concise and professional.

    Historical Memory Bank:
    {retrieved_context}

    User Question:
    {user_question}
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return response.text

# ==========================================
# MAIN INTERACTIVE TERMINAL
# ==========================================
if __name__ == "__main__":
    print("\n*** AGENT ONLINE. Type 'exit' to shut down. ***")
    
    # This creates an infinite loop so you can keep chatting with it
    while True:
        question = input("\nAsk the agent a question: ")
        
        if question.lower() == 'exit':
            print("Shutting down engine...")
            break
        
        answer = ask_agent(question)
        
        print("\n=== AGENT RESPONSE ===")
        print(answer)
        print("======================")