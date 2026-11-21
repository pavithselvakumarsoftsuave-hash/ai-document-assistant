"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat, documents
from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import Conversation, Document, Message  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare local storage and create database tables on startup."""
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI Document Assistant",
    description="Upload documents, ask grounded questions, and review conversation history.",
    version="1.0.0",
    lifespan=lifespan,
)
WEB_DIR = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Serve the local document chat interface."""
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Basic process health endpoint."""
    return {"status": "ok"}
