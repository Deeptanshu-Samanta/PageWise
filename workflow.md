# PDF RAG Website: Workflow

This document explains what happens inside the app in two situations:

1. A user **uploads a PDF** (indexing, done once per file)
2. A user **asks a question** (retrieval and answering, done for every question)

---

## Project structure

```
pdf-rag/
├── app.py            # Streamlit UI: uploader, model dropdown, chat
├── rag/
│   ├── parser.py     # PDF bytes -> list of page Documents
│   ├── chunker.py    # pages -> small overlapping chunks
│   ├── indexer.py    # chunks -> embeddings -> FAISS index
│   └── qna.py        # model dropdown logic, prompt, retrieval, streaming answer
├── requirements.txt
└── .env              # API keys (GROQ_API_KEY, GEMINI_API_KEY, ...)
```

---

## Part 1: When the user uploads a PDF

This runs **once per uploaded file**. It prepares the PDF so questions can be answered quickly later.

```
PDF file
  |
  v
[1] app.py        st.file_uploader gives the file bytes
  |
  v
[2] parser.py     load_pdf(): read each page's text with PyMuPDF
  |               -> list of Document(page_content, metadata={"page": n})
  v
[3] chunker.py    split_docs(): RecursiveCharacterTextSplitter
  |               (chunk_size=1000, chunk_overlap=200)
  |               -> many small chunks, each keeping its page number
  v
[4] indexer.py    HuggingFaceEmbeddings (all-MiniLM-L6-v2)
  |               turns every chunk into a vector (a list of numbers)
  v
[5] indexer.py    FAISS.from_documents(): stores all vectors in a
  |               searchable index (kept in memory)
  v
[6] app.py        index saved in st.session_state.index
                  -> the app is now ready for questions
```

### What each step does

| Step | File | What happens | Why |
|------|------|--------------|-----|
| 1 | `app.py` | The user picks a PDF; Streamlit gives us its bytes. | Entry point of the pipeline. |
| 2 | `parser.py` | Text is extracted page by page and each page becomes a `Document` with its page number in `metadata`. | We need the page number later for source citations. |
| 3 | `chunker.py` | Pages are cut into ~1000-character pieces that overlap by 200 characters. | Small chunks make retrieval precise. Overlap stops a sentence being cut in half and losing meaning. |
| 4 | `indexer.py` | The embedding model converts each chunk into a vector. Chunks with similar meaning get similar vectors. | This lets us search by meaning instead of exact keywords. |
| 5 | `indexer.py` | FAISS stores all the vectors in an index built for fast nearest-neighbour search. | Finding the closest chunks to a question takes milliseconds, even for big PDFs. |
| 6 | `app.py` | The index is stored in `st.session_state`. | Each user session gets its own index, so users never see each other's PDFs. |

### Things to know

- This is the **slow part** (embedding thousands of chunks takes time on a big PDF), so show a spinner or progress bar.
- It happens **only once per PDF**. Questions after that reuse the stored index.
- A **scanned PDF** (images of text) returns no text in step 2. It needs OCR first, so the app should show a clear error.
- Uploading a new PDF replaces the old index and clears the chat.

---

## Part 2: When the user asks a question

This runs **every time** the user sends a message.

```
User question + selected model (from the dropdown)
  |
  v
[1] app.py      st.chat_input receives the question;
  |             the sidebar selectbox gives the model label
  v
[2] qna.py      ask(question, index, model_label)
  |
  v
[3] qna.py      index.similarity_search(question, k=5)
  |             1. question -> vector (same embedding model as indexing)
  |             2. FAISS finds the 5 closest chunk vectors
  |             -> 5 relevant chunks (with page numbers)
  v
[4] qna.py      format_docs(): join the chunks into one text block:
  |             "Page 3: ...text...  Page 7: ...text..."
  v
[5] qna.py      prompt fills {context} and {question}
  |
  v
[6] qna.py      get_model(model_label) builds the chosen LLM
  |             (Groq / Gemini / Ollama)
  v
[7] qna.py      chain = prompt | model | StrOutputParser()
  |             chain.stream(...) sends the prompt to the LLM
  v
[8] app.py      st.write_stream(stream) shows the answer word by word
  |             and the source pages are shown under it
  v
Answer on screen + "Sources: pages 3, 7, 12"
```

### What each step does

| Step | File | What happens | Why |
|------|------|--------------|-----|
| 1 | `app.py` | Reads the question and which model the user selected. | The dropdown lets the user switch models between questions. |
| 2 | `qna.py` | `ask()` is called with the question, the index and the model label. | One function runs the whole answering flow. |
| 3 | `qna.py` | The question is embedded and FAISS returns the `k=5` most similar chunks. | **This is the "retrieval" in RAG.** The LLM never sees the whole PDF, only the relevant parts. |
| 4 | `qna.py` | The chunks are formatted into a single context string with page labels. | Gives the model readable context and lets it cite pages. |
| 5 | `qna.py` | The prompt template is filled with the context and the question. | Tells the model to answer **only** from the context and say "I don't know." if the answer isn't there. |
| 6 | `qna.py` | `get_model()` creates the selected LLM object. | The model is built fresh per question, so changing the dropdown takes effect immediately. |
| 7 | `qna.py` | The chain runs prompt, then model, then parser. The model generates the answer only when `stream` is consumed. | **This is the "generation" in RAG.** |
| 8 | `app.py` | `st.write_stream` pulls pieces from the generator and displays them as they arrive. | The user sees the answer start immediately instead of waiting for the full response. |

### Things to know

- Retrieval (step 3) is fast. Most of the time is spent waiting for the LLM (step 7).
- The **same embedding model** must be used for indexing and for questions. Otherwise the vectors aren't comparable and retrieval breaks.
- If the retrieved chunks don't contain the answer, the prompt makes the model say "I don't know." instead of guessing.
- Each question is **independent** (no chat history in this version). Follow-ups like "explain that more simply" won't work yet.
- The sources shown under the answer are the pages of the retrieved chunks, not necessarily every page the model used.

---

## Summary: the two phases

| | Upload (indexing) | Question (querying) |
|---|---|---|
| **When** | Once per PDF | Every question |
| **Speed** | Slow (seconds to minutes) | Fast retrieval, then LLM time |
| **Files used** | `parser.py`, `chunker.py`, `indexer.py` | `qna.py` |
| **Main tools** | PyMuPDF, text splitter, embeddings, FAISS | FAISS search, prompt, LLM (Groq/Gemini/Ollama) |
| **Output** | A FAISS index in `session_state` | A streamed answer plus source pages |

In one line: **upload** turns the PDF into a searchable index; **asking** finds the relevant chunks in that index and has the LLM answer from them.

---

## Possible upgrades later

- Chat history with question rewriting, so follow-ups work
- A reranker to improve which chunks are chosen
- Hybrid search (keyword plus embeddings)
- OCR for scanned PDFs
- Caching the index so re-uploading the same file is instant
- Multiple PDFs per session