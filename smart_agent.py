"""
OmniData Studio - Core Autonomous Agent
Implements Unified Event Streaming and Dynamic Signal Triage. The OS encodes 
all user actions into procedural memory, allowing the Cognitive Gatekeeper to 
dynamically route queries between Standard Reflex execution and Extended Cognition.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any
import chromadb
from groq import Groq
from sqlalchemy import create_engine, text
from config import config

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Infrastructure Initialization
# ---------------------------------------------------------------------------
try:
    groq_client = Groq(api_key=config.GROQ_API_KEY)
    engine = create_engine(config.SUPABASE_URL)
    
    chroma_client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)
    invoice_memory = chroma_client.get_or_create_collection(name="invoice_memory")
    os_memory = chroma_client.get_or_create_collection(name="os_memory")
except Exception as e:
    logger.error(f"Infrastructure initialization error: {e}")

# ---------------------------------------------------------------------------
# Procedural Memory & Semantic Tools
# ---------------------------------------------------------------------------
def log_os_event(action: str, details: str):
    """Encodes OS activities into the continuous procedural vector memory."""
    try:
        timestamp = datetime.now().isoformat()
        doc_id = f"evt_{timestamp.replace(':', '').replace('.', '')}"
        event_text = f"[{timestamp}] ACTION: {action} | DETAILS: {details}"
        os_memory.add(documents=[event_text], ids=[doc_id])
        logger.info(f"Procedural Memory Appended: {action}")
    except Exception as e:
        logger.error(f"Event logging failed: {e}")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_postgresql",
            "description": "Executes raw PostgreSQL. Use this ONLY when you need exact numbers, structural records, or need to manipulate data in the tables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The raw PostgreSQL string. Wrap column/table names in double quotes."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Searches the document vector database. Use this ONLY when the user asks about the contents of uploaded PDFs or unstructured text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "The semantic phrase to search for."}
                },
                "required": ["search_term"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# Core Cognitive Loop
# ---------------------------------------------------------------------------
def _get_live_schema() -> str:
    schema_info = ""
    try:
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")).fetchall()
            for table in tables:
                table_name = table[0]
                cols = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';")).fetchall()
                schema_info += f"Table '{table_name}': {', '.join([f'\"{c[0]}\" ({c[1]})' for c in cols])}\n"
        return schema_info
    except:
        return "Schema unavailable."

def process_cognitive_request(user_query: str, history: list = None) -> Dict[str, Any]:
    logger.info("Cognitive cycle initiated.")
    
    # 1. Log the incoming prompt
    log_os_event("User Query Received", user_query)

    # 2. Dynamic Signal Triage (The Gatekeeper)
    triage_prompt = f"""Evaluate this OS query: '{user_query}'
Does this require deep historical context (past UI actions, old imports, workflows) to answer, or is it a standard request?
Reply ONLY with 'STANDARD' or 'EXTENDED'."""

    try:
        triage_res = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": triage_prompt}],
            temperature=0.0,
            max_tokens=10
        )
        depth_signal = triage_res.choices[0].message.content.strip().upper()
        if "EXTENDED" not in depth_signal: depth_signal = "STANDARD"
    except:
        depth_signal = "STANDARD"

    logger.info(f"Signal Triage classified intent as: {depth_signal}")

    # 3. Assemble the Context Window
    schema = _get_live_schema()
    system_prompt = f"""You are OmniData, an intelligent Data Operating System assistant.
You have tools to execute SQL or search documents if you need facts. If you don't need facts, just talk to the user naturally.
CRITICAL: If the user replies "YES" to a security warning, you MUST immediately use the 'execute_postgresql' tool with the exact SQL query shown in the warning to finalize the execution.
LIVE POSTGRESQL SCHEMA CONTEXT:\n{schema}"""

    # Inject Extended Cognition if requested by the Gatekeeper
    if depth_signal == "EXTENDED":
        try:
            hist_results = os_memory.query(query_texts=[user_query], n_results=5)
            if hist_results['documents'] and len(hist_results['documents'][0]) > 0:
                system_prompt += f"\n\nDEEP PROCEDURAL MEMORY (Past OS Events):\n{chr(10).join(hist_results['documents'][0])}"
                logger.info("Deep Procedural Memory injected.")
        except Exception as e:
            logger.error(f"Failed to fetch procedural memory: {e}")

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history:
            if "System operational" not in msg["content"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_query})

    # 4. Autonomous Intent Analysis & Execution
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
            parallel_tool_calls=False
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        if response_message.content or tool_calls:
            messages.append(response_message.model_dump(exclude_unset=True))

    except Exception as e:
        error_str = str(e)
        if "tool_use_failed" in error_str and "<function=" in error_str:
            match = re.search(r'<function=(\w+)(.*?)</function>', error_str)
            if match:
                class MockFunc: name = match.group(1); arguments = match.group(2)
                class MockCall: id = "call_rec_1"; function = MockFunc()
                tool_calls = [MockCall()]
                messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": "call_rec_1", "type": "function", "function": {"name": match.group(1), "arguments": match.group(2)}}]})
            else:
                return {"status": "error", "response": "API Tool Parsing Error.", "route": "ERROR"}
        else:
            return {"status": "error", "response": str(e), "route": "ERROR"}

    try:
        if not tool_calls:
            final_content = response_message.content if hasattr(response_message, 'content') else ""
            log_os_event("AI Conceptual Response", final_content)
            return {"status": "success", "response": final_content, "route": "CHAT", "sql": None}

        executed_sql = None
        route = "CHAT"

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            if function_name == "execute_postgresql":
                route = "SQL"
                executed_sql = arguments.get("query")
                log_os_event("AI SQL Execution", executed_sql)
                
                # --- The Stateful Security Hold ---
                if any(k in executed_sql.upper() for k in ["DROP", "DELETE", "TRUNCATE"]):
                    # 1. Read the most recent assistant message from the memory payload
                    last_ast = next((m["content"] for m in reversed(history or []) if m["role"] == "assistant" and m["content"]), "")
                    
                    # 2. Check if the user is explicitly confirming the previous warning
                    confirmed = (
                        "⚠️ **WARNING: Destructive command detected.**" in last_ast and 
                        user_query.strip().upper() in ["YES", "Y", "CONFIRM"]
                    )
                    
                    if not confirmed:
                        log_os_event("Security Hold", f"Pending confirmation for: {executed_sql}")
                        return {
                            "status": "success", 
                            "response": f"⚠️ **WARNING: Destructive command detected.**\n\nI am about to execute the following query:\n`{executed_sql}`\n\nAre you absolutely sure you want to proceed? Reply **YES** to confirm or **NO** to cancel.", 
                            "route": "SECURITY HOLD", 
                            "sql": None
                        }
                    else:
                        logger.warning(f"User explicitly confirmed destructive SQL: {executed_sql}")

                try:
                    with engine.begin() as conn:
                        result = conn.execute(text(executed_sql))
                        tool_response = str([str(row) for row in result.fetchall()][:20]) if result.returns_rows else "Success. No rows returned."
                except Exception as e:
                    tool_response = f"SQL Error: {str(e)}"
                    
            elif function_name == "search_documents":
                route = "VECTOR"
                search_term = arguments.get("search_term")
                log_os_event("AI Vector Search", search_term)
                try:
                    results = invoice_memory.query(query_texts=[search_term], n_results=2)
                    tool_response = "\n".join(results['documents'][0]) if results['documents'] and len(results['documents'][0]) > 0 else "No context found."
                except Exception as e:
                    tool_response = f"Vector Error: {str(e)}"

            # CRITICAL: Append the tool response back into the context window
            messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": tool_response})

        final_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3
        )
        
        final_content = final_response.choices[0].message.content
        log_os_event("AI Synthesized Response", final_content)

        return {"status": "success", "response": final_content, "route": route, "sql": executed_sql}

    except Exception as e:
        logger.error(f"Agent Pipeline Error: {e}")
        return {"status": "error", "response": f"Internal failure: {str(e)}"}