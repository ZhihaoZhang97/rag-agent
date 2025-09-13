# Document RAG Backend Service

This FastAPI service provides document processing and RAG (Retrieval Augmented Generation) capabilities for the Agent Chat UI.

## Features

- Document upload and processing (PDF, TXT, DOCX)
- Document chunking and embedding
- Vector storage using Qdrant
- Semantic search across processed documents

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration (see `.env.example` for reference)

4. Run the service:
```bash
python run.py
```

The API will be available at http://localhost:8000

## API Endpoints

- `GET /` - Health check
- `POST /upload` - Upload and process a document
- `POST /query` - Query processed documents

## Integration with Agent Chat UI

This backend service can be integrated with the Agent Chat UI by updating the frontend to:

1. Send document uploads to this service
2. Query the RAG system for relevant information
3. Use the retrieved context to enhance AI responses
