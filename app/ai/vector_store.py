"""Create, save, and load document-scoped Chroma collections."""

from pathlib import Path
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument

from app.ai.embeddings import get_embeddings

DEFAULT_COLLECTION_NAME = "document_chunks"
ACTIVE_COLLECTION_FILE = ".active_collection"


def get_active_collection_name(index_path: Path) -> str:
    """Read the active Chroma collection name, supporting older indexes."""
    marker = index_path / ACTIVE_COLLECTION_FILE
    if not marker.exists():
        return DEFAULT_COLLECTION_NAME
    return marker.read_text(encoding="utf-8").strip() or DEFAULT_COLLECTION_NAME


def set_active_collection_name(index_path: Path, collection_name: str) -> None:
    """Atomically point a document index at a fully created collection."""
    if collection_name == DEFAULT_COLLECTION_NAME:
        (index_path / ACTIVE_COLLECTION_FILE).unlink(missing_ok=True)
        return
    marker = index_path / ACTIVE_COLLECTION_FILE
    temporary_marker = index_path / f"{ACTIVE_COLLECTION_FILE}.tmp"
    temporary_marker.write_text(collection_name, encoding="utf-8")
    os.replace(temporary_marker, marker)


def create_index(
    chunks: list[LCDocument],
    index_path: Path,
    collection_name: str | None = None,
) -> None:
    """Embed chunks and persist a Chroma collection to disk."""
    if not chunks:
        raise ValueError("There is no readable text to index.")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.mkdir(parents=True, exist_ok=True)
    selected_collection = collection_name or get_active_collection_name(index_path)
    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=str(index_path),
        collection_name=selected_collection,
    )
    if collection_name:
        set_active_collection_name(index_path, selected_collection)


def load_index(index_path: Path) -> Chroma:
    """Load a local Chroma collection created by this application."""
    if not index_path.exists():
        raise FileNotFoundError("The document search index is missing.")
    return Chroma(
        persist_directory=str(index_path),
        embedding_function=get_embeddings(),
        collection_name=get_active_collection_name(index_path),
    )


def delete_collection(index_path: Path, collection_name: str) -> None:
    """Delete an inactive collection after a replacement is safely active."""
    if collection_name == get_active_collection_name(index_path):
        return
    collection = Chroma(
        persist_directory=str(index_path),
        embedding_function=get_embeddings(),
        collection_name=collection_name,
    )
    collection.delete_collection()
