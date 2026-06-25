# OmniData Studio: Agentic Data Operating System

OmniData Studio is a multi-agent cognitive architecture designed to bridge the gap between unstructured semantic data and strict relational databases. It serves as an AI-native workspace where natural language instructions are compiled into deterministic database operations, enabling seamless data analysis and management.

## Core AI Capabilities

OmniData utilizes a multi-agent workflow to ensure high-accuracy, context-aware interaction with your data environment.

* **Cognitive Router (Llama-3.1-8B):** Operates as the deterministic gatekeeper. It classifies incoming queries in milliseconds, routing them strictly to either the SQL execution engine or the Vector RAG (Retrieval-Augmented Generation) engine based on intent.
* **Database Engineer Agent (Llama-3.3-70B):** Handles structural data manipulation. It performs live schema introspection to understand data types and table relationships, then translates natural language into type-safe PostgreSQL syntax.
* **Semantic Analyst Agent (ChromaDB + Llama-3.3-70B):** Manages unstructured data. It utilizes local high-dimensional vector embeddings to perform semantic search, grounding the AI’s reasoning in relevant historical context.
* **Multi-Modal ETL Pipeline:** An intelligent API gateway that handles diverse inputs:
* **Deterministic:** Automatically parses CSV files into Pandas DataFrames for immediate SQL insertion.
* **Multi-Modal:** Leverages Google Gemini 2.5 Flash to parse complex PDF invoices, extracting structured JSON entities while performing a dual-write operation: relational data to PostgreSQL and raw semantic text to ChromaDB.



## Technical Specifications

* **Frontend:** Next.js 15, React, Tailwind CSS, Base UI, TypeScript.
* **Backend:** Python 3.12, FastAPI, SQLAlchemy, Pandas.
* **AI Orchestration:** Groq API (Llama-3 models), Google GenAI API (Gemini).
* **Databases:** Supabase (PostgreSQL), ChromaDB (Vector Storage).

## Requirements

Before running the application, ensure your local environment is configured with:

1. **Python 3.12+** (with the `pip` package manager).
2. **Node.js 18+** (with `npm`).
3. **API Keys:** Valid keys for the following services:
* Supabase (PostgreSQL Connection URI)
* Groq API
* Google GenAI API



## Installation and Usage

### 1. Clone the Repository

```bash
git clone https://github.com/C4RB0Nite/omnidata-studio.git
cd "OmniData Studio"

```

### 2. Configuration

Create a `.env` file in the root directory and populate it with your credentials:

```text
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
SUPABASE_URL=postgresql://your_connection_uri

```

### 3. Execution

The repository includes a launch script that automates environment verification and server startup.

**For Windows:**
Double-click `start.bat` or run:

```cmd
.\start.bat

```

**For Mac/Linux:**

```bash
chmod +x start_mac_linux.sh
./start_mac_linux.sh

```

Upon execution, the script will verify your dependencies, boot the backend API on port 8000, and launch the frontend interface on port 3000.

## License

Distributed under the MIT License.

## Connect

Developed by **C4RB0Nite**.

Follow for updates and AI engineering insights: [https://x.com/C4RB0Nite](https://x.com/C4RB0Nite)