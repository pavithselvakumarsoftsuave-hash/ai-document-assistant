# AI Document Assistant

A beginner-friendly local web app that accepts PDF, DOCX, and TXT files, builds a searchable ChromaDB collection for each file, and answers questions with retrieval-augmented generation (RAG). The browser UI and FastAPI backend run together; SQLite stores document metadata and conversation history.

## How the pieces fit together

1. The document route accepts an upload and validates its extension and size.
2. The document service extracts text with PyPDF, python-docx, or Python's UTF-8 reader.
3. LangChain splits text into overlapping chunks. HuggingFace sentence-transformers embeds each chunk, and ChromaDB saves a separate persistent collection per document.
4. The chat route selects one document, retrieves relevant chunks from only that document, and asks the configured OpenAI chat model to answer only from those excerpts. Conversation history can clarify follow-up references but is not answer evidence.
5. User and assistant messages are saved in SQLite and can be fetched later by conversation ID.

## Requirements

- Python 3.10 or newer
- A provider key for question answering: Hugging Face, Gemini, or OpenAI
- Internet access on the first run to download the HuggingFace embedding model

## Install and run

From the project root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set the key for your provider. To use Gemini, set `LLM_PROVIDER=gemini` and provide `GEMINI_API_KEY`; Gemini is a low-cost default. For Hugging Face, set `LLM_PROVIDER=huggingface` and provide `HF_API_KEY`. To use OpenAI, set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY`. Then start the API:

```powershell
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> for the document chat UI, or <http://127.0.0.1:8000/docs> for interactive Swagger documentation. Upload a document in the left panel, select it, and ask questions in the chat box. The app creates `data/assistant.db`, upload files, and Chroma collections under `data/` on startup. Keep `.env` private.

The upload and indexing workflow works without an API key, but chat answers need a valid key and available usage for the selected provider. The default Hugging Face model is `Qwen/Qwen3.5-9B:fastest`; `:fastest` asks Hugging Face to route to its highest-throughput provider. The Gemini default is `gemini-3.5-flash-lite`. Restart the server after editing `.env` so the new settings are loaded. On the first upload, the HuggingFace embedding model downloads into `.model-cache` and may take a few minutes; later runs load it locally.

## API overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Check that the API is running |
| `POST` | `/api/v1/documents/upload` | Upload one PDF, DOCX, or TXT document (`multipart/form-data`, field `file`) |
| `GET` | `/api/v1/documents` | List indexed documents |
| `POST` | `/api/v1/documents/{document_id}/reindex` | Re-extract a stored upload and rebuild its chunks/index |
| `DELETE` | `/api/v1/documents/{document_id}` | Remove a document and its index |
| `POST` | `/api/v1/chat` | Ask a question and save it to a conversation |
| `GET` | `/api/v1/conversations` | List saved conversations |
| `GET` | `/api/v1/conversations/{conversation_id}` | Read a conversation's complete message history |

Example chat body:

```json
{
  "question": "What are the main conclusions?",
  "document_id": "document-id-from-upload",
  "conversation_id": null
}
```

Pass the returned `conversation_id` in later chat requests to continue that conversation. Every chat request names exactly one `document_id`; the backend retrieves from only that document's collection. Answers include source chunks and are instructed to say when the selected document does not contain the answer.

## Configuration

All settings can be placed in `.env`. Defaults are documented in `.env.example`: model name, embedding model, SQLite URL, data folder, maximum upload size, chunk size/overlap, number of retrieved chunks, and the minimum retrieval relevance score. Low relevance matches are rejected and answered with an explicit "not found" response. The embedding model runs locally; OpenAI is used for answer generation.

## Notes

- The initial HuggingFace model download can take a while.
- Chroma collections are stored locally under `data/indexes/`. Protect the `data/` directory from untrusted writes.
- This starter backend does not implement user authentication or per-user access control. Add those before exposing it to multiple untrusted users.
