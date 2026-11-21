const API = "/api/v1";
const state = { documents: [], selectedDocumentId: null, conversationId: null, busy: false, uploading: false };

const elements = {
  uploadForm: document.querySelector("#upload-form"), fileInput: document.querySelector("#file-input"),
  uploadButton: document.querySelector("#upload-button"), uploadStatus: document.querySelector("#upload-status"),
  selectedFileInfo: document.querySelector("#selected-file-info"),
  selectedFileType: document.querySelector("#selected-file-type"),
  selectedFileName: document.querySelector("#selected-file-name"),
  clearSelectedFile: document.querySelector("#clear-selected-file"),
  documentList: document.querySelector("#document-list"), refresh: document.querySelector("#refresh-documents"),
  welcome: document.querySelector("#welcome"), messages: document.querySelector("#messages"),
  form: document.querySelector("#chat-form"), input: document.querySelector("#question-input"),
  send: document.querySelector("#send-button"), error: document.querySelector("#chat-error"),
  newChat: document.querySelector("#new-chat"),
};

function updateSelectedFile() {
  const file = elements.fileInput.files[0];
  elements.selectedFileInfo.hidden = !file;
  elements.uploadButton.disabled = !file || state.uploading;
  elements.uploadButton.textContent = state.uploading ? "Indexing…" : "Upload document";
  if (!file) {
    elements.selectedFileType.textContent = "";
    elements.selectedFileName.textContent = "";
    elements.selectedFileName.removeAttribute("title");
    return;
  }
  elements.selectedFileType.textContent = file.name.includes(".") ? file.name.split(".").pop().toUpperCase() : "FILE";
  elements.selectedFileName.textContent = file.name;
  elements.selectedFileName.title = file.name;
}

function setError(message = "") {
  elements.error.textContent = message;
  elements.error.classList.toggle("visible", Boolean(message));
}

function setChatEnabled(enabled) {
  elements.input.disabled = !enabled;
  elements.send.disabled = !enabled || state.busy;
  elements.input.placeholder = enabled
    ? "Ask a question about this document…"
    : "Upload and select a document to start asking questions…";
}

function renderDocuments() {
  elements.documentList.replaceChildren();
  if (!state.documents.length) {
    const empty = document.createElement("p");
    empty.className = "empty-documents";
    empty.textContent = "Your uploaded documents will appear here.";
    elements.documentList.append(empty);
    return;
  }
  for (const documentRecord of state.documents) {
    const row = document.createElement("div");
    row.className = "document-row";
    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.className = `document-item${documentRecord.id === state.selectedDocumentId ? " selected" : ""}`;
    selectButton.setAttribute("aria-pressed", String(documentRecord.id === state.selectedDocumentId));
    const icon = document.createElement("span");
    icon.className = "file-icon";
    icon.textContent = documentRecord.file_type.toUpperCase();
    const details = document.createElement("span");
    details.className = "document-name";
    const name = document.createElement("span");
    name.textContent = documentRecord.filename;
    const meta = document.createElement("span");
    meta.className = "document-meta";
    meta.textContent = `${documentRecord.chunk_count} text chunks`;
    details.append(name, meta);
    selectButton.append(icon, details);
    selectButton.addEventListener("click", () => selectDocument(documentRecord.id));

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "document-delete";
    removeButton.title = `Remove ${documentRecord.filename}`;
    removeButton.setAttribute("aria-label", `Remove ${documentRecord.filename}`);
    removeButton.textContent = "×";
    removeButton.addEventListener("click", async () => {
      if (!window.confirm(`Remove “${documentRecord.filename}” and its search index?`)) return;
      removeButton.disabled = true;
      try {
        const response = await fetch(`${API}/documents/${documentRecord.id}`, { method: "DELETE" });
        if (!response.ok) throw new Error("Could not remove this document.");
        await loadDocuments();
        elements.uploadStatus.textContent = `Removed ${documentRecord.filename}.`;
      } catch (error) {
        setError(error.message);
      } finally {
        removeButton.disabled = false;
      }
    });
    row.append(selectButton, removeButton);
    elements.documentList.append(row);
  }
}

function selectDocument(documentId) {
  if (state.selectedDocumentId !== documentId) {
    state.selectedDocumentId = documentId;
    state.conversationId = null;
    elements.messages.replaceChildren();
    elements.messages.classList.remove("active");
    elements.welcome.hidden = false;
    setError("");
  }
  setChatEnabled(Boolean(documentId));
  renderDocuments();
}

async function loadDocuments(preferredId = null) {
  const response = await fetch(`${API}/documents`);
  if (!response.ok) throw new Error("Could not load the document list.");
  state.documents = await response.json();
  const preferredExists = state.documents.some((item) => item.id === preferredId);
  const currentExists = state.documents.some((item) => item.id === state.selectedDocumentId);
  const selectedId = preferredExists ? preferredId : currentExists ? state.selectedDocumentId : state.documents[0]?.id ?? null;
  renderDocuments();
  if (selectedId !== state.selectedDocumentId) selectDocument(selectedId);
  else {
    setChatEnabled(Boolean(selectedId));
    renderDocuments();
  }
}

function addMessage(role, content) {
  elements.welcome.hidden = true;
  elements.messages.classList.add("active");
  const row = document.createElement("div");
  row.className = `message ${role}`;
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.textContent = role === "assistant" ? "✳" : "Y";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  row.append(avatar, bubble);
  elements.messages.append(row);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return row;
}

elements.uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = elements.fileInput.files[0];
  if (!file) return;
  state.uploading = true;
  elements.uploadButton.disabled = true;
  updateSelectedFile();
  elements.uploadStatus.textContent = "Extracting text and preparing document search…";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API}/documents/upload`, { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Upload failed.");
    elements.uploadStatus.textContent = `Ready · ${result.chunk_count} searchable chunks`;
    await loadDocuments(result.id);
    elements.fileInput.value = "";
    updateSelectedFile();
  } catch (error) {
    elements.uploadStatus.textContent = error.message;
  } finally {
    state.uploading = false;
    updateSelectedFile();
  }
});

elements.fileInput.addEventListener("change", updateSelectedFile);
elements.clearSelectedFile.addEventListener("click", () => {
  elements.fileInput.value = "";
  elements.uploadStatus.textContent = "";
  updateSelectedFile();
});

elements.refresh.addEventListener("click", async () => {
  try { await loadDocuments(); } catch (error) { setError(error.message); }
});

elements.newChat.addEventListener("click", () => {
  state.conversationId = null;
  elements.messages.replaceChildren();
  elements.messages.classList.remove("active");
  elements.welcome.hidden = false;
  elements.input.value = "";
  setError("");
  elements.input.focus();
});

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = elements.input.value.trim();
  if (!question || !state.selectedDocumentId || state.busy) return;
  setError("");
  addMessage("user", question);
  elements.input.value = "";
  elements.input.style.height = "auto";
  state.busy = true;
  setChatEnabled(true);
  const waiting = addMessage("assistant", "Looking through your document…");
  waiting.querySelector(".bubble").classList.add("typing");
  try {
    const response = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: state.conversationId, document_id: state.selectedDocumentId }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not get an answer.");
    state.conversationId = result.conversation_id;
    waiting.remove();
    addMessage("assistant", result.answer);
  } catch (error) {
    waiting.remove();
    setError(error.message);
  } finally {
    state.busy = false;
    setChatEnabled(Boolean(state.selectedDocumentId));
    elements.input.focus();
  }
});

elements.input.addEventListener("input", () => {
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 150)}px`;
});

elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    if (!state.selectedDocumentId) {
      elements.uploadStatus.textContent = "Upload and select a document first.";
      return;
    }
    elements.input.value = button.dataset.question;
    elements.input.focus();
    elements.input.style.height = `${elements.input.scrollHeight}px`;
  });
});

loadDocuments().catch((error) => setError(error.message));
