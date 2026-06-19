# Cognitive AI Document Agent (RAG Architecture)

## Overview
An enterprise-grade Retrieval-Augmented Generation (RAG) pipeline. This system doesn't just read documents; it forms procedural memories. It extracts unstructured data from PDFs, encodes the semantic meaning into a local Vector Database, and utilizes a central LLM reasoning engine to answer financial queries based on historical context.

## System Architecture
1. **Ingestion Layer:** Utilizes `PyPDF2` to scrape raw text from batch invoices and forces Google GenAI to format the chaotic text into strict JSON schemas.
2. **Semantic Memory Bank:** Integrates `ChromaDB` to convert textual JSON data into high-dimensional vector embeddings, allowing for meaning-based (semantic) data retrieval rather than flat keyword matching.
3. **Central Reasoning Engine:** A Python-based executive controller that intercepts user queries, retrieves mathematically relevant historical context from the Vector DB, and routes the combined payload to the AI for highly accurate, context-aware decision making.

## Tech Stack
* Python 3.x
* Google GenAI API (Gemini 2.5 Flash)
* ChromaDB (Local Vector Storage)
* PyPDF2

## Why this matters
This modular RAG architecture completely eliminates the hallucination risks of standard LLMs by grounding the AI's reasoning entirely in a closed-loop, mathematically retrievable historical database.