from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class QueryRequest(BaseModel):
    query: str
    document_ids: Optional[List[str]] = None


class DocumentChunk(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


class QueryResponse(BaseModel):
    results: List[DocumentChunk]


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunks: int
    status: str
