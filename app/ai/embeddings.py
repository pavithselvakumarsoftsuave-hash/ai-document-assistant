"""Shared HuggingFace embedding model factory."""

from functools import lru_cache
import os

from langchain_core.embeddings import Embeddings

from app.core.config import get_settings


class LocalHuggingFaceEmbeddings(Embeddings):
    """LangChain adapter for a locally run HuggingFace sentence-transformer."""

    def __init__(self, model_name: str) -> None:
        cache_dir = get_settings().hf_home.resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(cache_dir))
        from sentence_transformers import SentenceTransformer

        try:
            self.model = SentenceTransformer(model_name, local_files_only=True)
        except (OSError, ValueError):
            # Download only when this model is not already present in the local HF cache.
            self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vector.tolist()


@lru_cache
def get_embeddings() -> LocalHuggingFaceEmbeddings:
    """Load the configured sentence-transformer once per process."""
    return LocalHuggingFaceEmbeddings(model_name=get_settings().embedding_model)
