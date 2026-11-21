"""Document upload, listing, and deletion endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import ingest_upload, list_documents, reindex_document, remove_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentResponse:
    """Upload a PDF, DOCX, or TXT file and build its vector index."""
    try:
        return await ingest_upload(file, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {error}") from error


@router.get("", response_model=list[DocumentResponse])
def get_documents(db: Session = Depends(get_db)) -> list[DocumentResponse]:
    """List all indexed documents."""
    return list_documents(db)


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
def reindex_uploaded_document(document_id: str, db: Session = Depends(get_db)) -> DocumentResponse:
    """Rebuild a document's chunks and embeddings from its stored original file."""
    try:
        result = reindex_document(document_id, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Document reindexing failed: {error}") from error
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return result


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a document and its local files."""
    if not remove_document(document_id, db):
        raise HTTPException(status_code=404, detail="Document not found.")
