# 📄 PageWise

**Chat with any PDF.** Upload a document, ask questions in plain English, and get answers grounded in the PDF, with the source page numbers shown under every reply.

PageWise is a Retrieval-Augmented Generation (RAG) web app built with Streamlit, LangChain, FAISS and your choice of LLM (Groq or Gemini).

## Features

- Upload large PDFs and ask questions about them
- Answers come only from the document, and the app says "I don't know." when the answer isn't there
- Source page numbers shown under each answer
- Switch between models from a dropdown
- Streaming responses, so answers appear word by word
- Adjustable number of retrieved chunks
- Each user session gets its own index, so PDFs are never mixed up
- Local embeddings (ONNX), so no PyTorch install is needed

## How it works

**When you upload a PDF (once per file)**

```
PDF -> parse pages (PyMuPDF) -> split into chunks -> embed (FastEmbed) -> FAISS index
```

**When you ask a question (every time)**

```
Question -> embed -> find the top-k similar chunks in FAISS
         -> build prompt (context + question) -> LLM -> streamed answer + source pages
```

See [workflow.md](workflow.md) for the full step-by-step explanation.

## Project structure

```
PageWise/
├── app.py              # Streamlit UI: uploader, model dropdown, chat
├── rag/
│   ├── parser.py       # PDF bytes -> page Documents
│   ├── chunker.py      # pages -> overlapping chunks
│   ├── indexer.py      # chunks -> embeddings -> FAISS index
│   └── qna_model.py    # model registry, prompt, retrieval, streaming answer
├── requirements.txt
├── workflow.md
└── .env                # your API keys (not committed)
```

## Tech stack

| Part | Tool |
|---|---|
| UI | Streamlit |
| PDF parsing | PyMuPDF |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | FastEmbed (`all-MiniLM-L6-v2`) |
| Vector store | FAISS |
| LLMs | Groq (GPT-OSS) and Google Gemini through LangChain |

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/PageWise.git
cd PageWise
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

Python 3.10 to 3.12 is recommended.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API keys

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here
```

You only need the keys for the providers you want to use. The model dropdown shows only models whose key is set.

- Groq key: https://console.groq.com
- Gemini key: https://aistudio.google.com

### 5. Run the app

```bash
streamlit run app.py
```

If the `streamlit` command is blocked on your system (for example by a Windows application control policy), run it through Python instead:

```bash
python -m streamlit run app.py
```

Then open http://localhost:8501.

## Configuration

- **Models:** edit the `models` dictionary in `rag/qna_model.py` to add or remove options. Provider model IDs change often, so check the provider's current model list if you get a "model not found" error.
- **Chunking:** change `chunk_size` and `chunk_overlap` in `rag/chunker.py` (defaults: 1000 / 200).
- **Upload limit:** change `MAX_MB` at the top of `app.py` (default: 50).

## Limitations

- Scanned PDFs (images of text) are not supported yet, because there is no OCR step.
- Each question is answered independently, so follow-ups like "explain that more simply" don't use earlier messages.
- The index lives in memory, so it is lost when the session ends.

