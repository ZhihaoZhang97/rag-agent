from fastapi import FastAPI, UploadFile, File, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from typing import List
from .services.document_service import (
    process_document,
    list_documents,
    delete_document,
)
from .models.schemas import DocumentInfo

app = FastAPI(title="Document RAG API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Document RAG API is running"}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document for RAG
    """
    # Check file type
    if not file.filename.endswith((".pdf", ".txt", ".docx", ".md", ".markdown")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF, TXT, MD/MARKDOWN, and DOCX are supported.",
        )

    try:
        # Generate a unique ID for this document
        doc_id = str(uuid.uuid4())

        # Save and process the document
        result = await process_document(file, doc_id)

        return {
            "document_id": doc_id,
            "filename": file.filename,
            "chunks": result["chunk_count"],
            "status": "processed",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing document: {str(e)}"
        )


@app.get("/documents", response_model=List[DocumentInfo])
async def get_documents():
    """
    List all documents in the database
    """
    try:
        documents = await list_documents()
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing documents: {str(e)}"
        )


@app.delete("/documents/{document_id}")
async def remove_document(
    document_id: str = Path(..., description="The ID of the document to delete")
):
    """
    Delete a document from the database
    """
    try:
        success = await delete_document(document_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Document with ID {document_id} not found"
            )
        return {"status": "success", "message": f"Document {document_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}"
        )
