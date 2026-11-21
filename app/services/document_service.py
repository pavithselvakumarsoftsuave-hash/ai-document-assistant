"""Document validation, text extraction, chunking, and indexing."""

from pathlib import Path
import unicodedata
from uuid import uuid4

from docx import Document as WordDocument
from fastapi import UploadFile
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.ai.vector_store import (
    create_index,
    delete_collection,
    get_active_collection_name,
    set_active_collection_name,
)
from app.core.config import get_settings
from app.models.document import Document

SUPPORTED_TYPES = {".pdf", ".docx", ".txt"}


def _extract_text(path: Path, extension: str) -> str:
    """Extract plain text from a supported file on disk."""
    if extension == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if extension == ".docx":
        document = WordDocument(str(path))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            paragraphs.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        return "\n".join(paragraphs)
    return path.read_text(encoding="utf-8-sig")


def _split_text(text: str, filename: str) -> list[LCDocument]:
    """Normalize extracted text and split it into indexed passages."""
    settings = get_settings()
    normalized_text = unicodedata.normalize("NFKC", text).strip()
    if not normalized_text:
        raise ValueError("No readable text was found in this document.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=min(settings.chunk_overlap, settings.chunk_size - 1),
        add_start_index=True,
    )
    chunks = splitter.create_documents([normalized_text], metadatas=[{"source": filename}])
    for number, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk"] = number
    return chunks


async def ingest_upload(upload: UploadFile, db: Session) -> Document:
    """Validate, store, parse, split, and index one uploaded document."""
    settings = get_settings()
    original_name = Path(upload.filename or "document").name
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_TYPES:
        raise ValueError("Unsupported file type. Upload a PDF, DOCX, or TXT file.")

    document_id = str(uuid4())
    target = settings.upload_dir / f"{document_id}{extension}"
    index_path = settings.index_dir / document_id
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    try:
        with target.open("wb") as output:
            while block := await upload.read(1024 * 1024):
                total_bytes += len(block)
                if total_bytes > settings.max_upload_size_mb * 1024 * 1024:
                    raise ValueError(f"File exceeds the {settings.max_upload_size_mb} MB upload limit.")
                output.write(block)
        if total_bytes == 0:
            raise ValueError("The uploaded file is empty.")

        text = _extract_text(target, extension)
        chunks = _split_text(text, original_name)
        create_index(chunks, index_path)

        record = Document(
            id=document_id,
            filename=original_name,
            file_type=extension.lstrip("."),
            stored_path=str(target),
            chunk_count=len(chunks),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        target.unlink(missing_ok=True)
        if index_path.exists():
            import shutil

            shutil.rmtree(index_path, ignore_errors=True)
        raise
    finally:
        await upload.close()


def list_documents(db: Session) -> list[Document]:
    """Return uploaded documents, newest first."""
    return db.query(Document).order_by(Document.created_at.desc()).all()


def reindex_document(document_id: str, db: Session) -> Document | None:
    """Re-extract and replace one document's index, preserving its document ID."""
    settings = get_settings()
    record = db.get(Document, document_id)
    if record is None:
        return None
    source_path = Path(record.stored_path)
    if not source_path.is_file():
        raise ValueError("The original uploaded file is missing and cannot be reindexed.")

    chunks = _split_text(_extract_text(source_path, source_path.suffix.lower()), record.filename)
    index_path = settings.index_dir / document_id
    old_collection = get_active_collection_name(index_path) if index_path.exists() else None
    new_collection = f"document_chunks_{uuid4().hex[:12]}"
    create_index(chunks, index_path, collection_name=new_collection)
    try:
        record.chunk_count = len(chunks)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        if old_collection:
            set_active_collection_name(index_path, old_collection)
        else:
            set_active_collection_name(index_path, "document_chunks")
        raise
    if old_collection:
        delete_collection(index_path, old_collection)
    return record


def remove_document(document_id: str, db: Session) -> bool:
    """Delete document metadata, original upload, and its vector index."""
    record = db.get(Document, document_id)
    if record is None:
        return False
    Path(record.stored_path).unlink(missing_ok=True)
    index_path = get_settings().index_dir / document_id
    if index_path.exists():
        import shutil

        shutil.rmtree(index_path, ignore_errors=True)
    db.delete(record)
    db.commit()
    return True
