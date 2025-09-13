import os
import time
import tempfile
from fastapi import UploadFile
from typing import Dict, List, Any
import logging

from dotenv import load_dotenv
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain.schema import Document
from langchain_community.embeddings.dashscope import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

logger = logging.getLogger(__name__)

DASHSCOPE_MODEL = os.getenv("DASHSCOPE_EMBEDDINGS_MODEL", "text-embedding-v4")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# If DASHSCOPE_API_KEY is not provided here, DashScopeEmbeddings will read it
# from the environment variable DASHSCOPE_API_KEY internally.
embeddings = (
    DashScopeEmbeddings(model=DASHSCOPE_MODEL, dashscope_api_key=DASHSCOPE_API_KEY)
    if DASHSCOPE_API_KEY
    else DashScopeEmbeddings(model=DASHSCOPE_MODEL)
)
vector_store = None
_embedding_dimension = None  # lazily determined
_persist_directory = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "data",
    "vectordb",
)


def load_documents(file_path: str, filename: str) -> List[Document]:
    """Load documents from a local path using format-specific loaders.

    - PDF: PyPDFLoader
    - TXT: TextLoader
    - MD/MARKDOWN: UnstructuredMarkdownLoader
    - DOCX: Docx2txtLoader
    """
    filename_lower = filename.lower()
    try:
        if filename_lower.endswith(".pdf"):
            docs = PyPDFLoader(file_path).load()
            logger.info(
                "PyPDFLoader loaded %d document(s) for '%s'", len(docs), filename
            )
            return docs
        if filename_lower.endswith((".md", ".markdown")):
            docs = UnstructuredMarkdownLoader(file_path).load()
            logger.info(
                "UnstructuredMarkdownLoader loaded %d document(s) for '%s'",
                len(docs),
                filename,
            )
            return docs
        if filename_lower.endswith(".txt"):
            docs = TextLoader(file_path, encoding="utf-8").load()
            logger.info(
                "TextLoader loaded %d document(s) for '%s'", len(docs), filename
            )
            return docs
        if filename_lower.endswith(".docx"):
            docs = Docx2txtLoader(file_path).load()
            logger.info(
                "Docx2txtLoader loaded %d document(s) for '%s'", len(docs), filename
            )
            return docs
        raise ValueError("Unsupported file type. Allowed: pdf, txt, md/markdown, docx")
    except Exception as e:
        logger.exception("Failed to load document '%s': %s", filename, str(e))
        raise


def _ensure_persist_dir() -> None:
    try:
        os.makedirs(_persist_directory, exist_ok=True)
    except Exception:
        pass


# Initialize the vector store
def init_vector_store():
    global vector_store
    if vector_store is None:
        _ensure_persist_dir()
        vector_store = Chroma(
            collection_name="documents",
            embedding_function=embeddings,
            persist_directory=_persist_directory,
        )
        logger.info(
            "Chroma vector store initialized (collection=%s, dir=%s)",
            "documents",
            _persist_directory,
        )
    return vector_store


async def process_document(file: UploadFile, doc_id: str) -> Dict[str, Any]:
    """Process an uploaded document and store it in the vector database"""
    # Ensure vector store env is initialized
    _ = init_vector_store()

    # Create a temporary file to save the uploaded file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename)[1]
    ) as temp_file:
        # Write the uploaded file content to the temp file
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Load the document(s) from disk
        t0 = time.time()
        documents = load_documents(temp_path, file.filename)
        logger.info(
            "Loaded %d document(s) for '%s' in %.2fs",
            len(documents),
            file.filename,
            time.time() - t0,
        )

        # Add document metadata
        for doc in documents:
            doc.metadata["document_id"] = doc_id
            doc.metadata["filename"] = file.filename

        # Split the document into semantic chunks using DashScope embeddings
        t1 = time.time()
        text_splitter = SemanticChunker(embeddings)
        chunks: List[Document] = []
        for d in documents:
            pieces = text_splitter.create_documents(
                [d.page_content], metadatas=[d.metadata]
            )
            chunks.extend(pieces)
        logger.info(
            "Semantic chunking produced %d chunk(s) for '%s' in %.2fs",
            len(chunks),
            file.filename,
            time.time() - t1,
        )

        # Add chunks to local Chroma vector store
        t2 = time.time()
        try:
            vs = init_vector_store()
            vs.add_documents(chunks)
            # Persist to disk after adding
            vs.persist()
            logger.info(
                "Chroma upsert success for '%s' (%d chunks) in %.2fs (dir=%s)",
                file.filename,
                len(chunks),
                time.time() - t2,
                _persist_directory,
            )
        except Exception as e:
            logger.exception(
                "Chroma upsert failed for '%s': %s: %s",
                file.filename,
                type(e).__name__,
                str(e),
            )
            raise

        return {"document_id": doc_id, "chunk_count": len(chunks), "status": "success"}

    finally:
        # Clean up the temp file
        os.unlink(temp_path)


async def list_documents() -> List[Dict[str, Any]]:
    """List documents aggregated by filename using Milvus filter-style query on JSON metadata.

    Returns a list of objects with `document_id` set to the filename so the
    frontend can use filename as the stable key and for deletion.
    """
    try:
        vs = init_vector_store()
        # Access underlying Chroma collection to fetch metadatas
        raw = vs._collection.get(include=["metadatas"])  # type: ignore[attr-defined]
        metadatas = raw.get("metadatas", []) if isinstance(raw, dict) else []
        documents_by_filename: Dict[str, Dict[str, Any]] = {}
        for md in metadatas:
            # chroma returns list of metadatas; each md is a dict
            meta = md or {}
            filename = meta.get("filename")
            if not filename:
                continue
            if filename not in documents_by_filename:
                documents_by_filename[filename] = {
                    "document_id": filename,
                    "filename": filename,
                    "chunks": 0,
                    "status": "processed",
                }
            documents_by_filename[filename]["chunks"] += 1
        return list(documents_by_filename.values())
    except Exception as e:
        logger.exception(
            "Failed to list documents from Chroma (dir=%s): %s: %s",
            _persist_directory,
            type(e).__name__,
            str(e),
        )
        return []


async def delete_document(filename: str) -> bool:
    """Delete all chunks for a file using its filename as the filter key.

    Note: The `document_id` parameter is treated as the filename.
    """
    try:
        vs = init_vector_store()
        # Delete by metadata filter
        vs._collection.delete(where={"filename": filename})  # type: ignore[attr-defined]
        return True
    except Exception as e:
        logger.exception(
            "Failed to delete document by filename from Chroma (dir=%s, filename=%s): %s: %s",
            _persist_directory,
            filename,
            type(e).__name__,
            str(e),
        )
        return False
