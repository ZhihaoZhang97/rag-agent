/**
 * Service for interacting with the document processing backend
 */

// Set this to your FastAPI backend URL
const DOCUMENT_API_URL = process.env.NEXT_PUBLIC_DOCUMENT_API_URL || 'http://localhost:8000';

export interface DocumentInfo {
  document_id: string;
  filename: string;
  chunks: number;
  status: string;
}

export interface DocumentQueryResult {
  content: string;
  metadata: Record<string, any>;
  score: number;
}

/**
 * Upload a document to the backend for processing
 */
export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${DOCUMENT_API_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload document');
  }

  return response.json();
}

/**
 * Delete a document from the database
 * Note: This assumes your backend has a delete endpoint
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${DOCUMENT_API_URL}/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete document');
  }
}

/**
 * List all documents in the database
 * Note: This assumes your backend has a list endpoint
 */
export async function listDocuments(): Promise<DocumentInfo[]> {
  const response = await fetch(`${DOCUMENT_API_URL}/documents`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list documents');
  }

  return response.json();
}
