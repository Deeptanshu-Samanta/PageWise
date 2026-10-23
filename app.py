import hashlib
import streamlit as st

from rag.indexer import build_index
from rag.qna_model import available_models, ask

MAX_MB = 50

st.set_page_config(page_title="Chat with your PDF", page_icon="📄", layout="wide")
st.title("📄 Chat with your PDF")

# ---------- SESSION STATE ----------
# index        -> FAISS index of the current PDF
# file_hash    -> identifies the current PDF so we only re-index when it changes
# file_name    -> shown in the sidebar
# messages     -> chat history for display: {"role", "content", "pages"}
for key, default in {
    "index": None,
    "file_hash": None,
    "file_name": None,
    "messages": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.header("Settings")

    models = available_models()
    if not models:
        st.error(
            "No models available. Add GROQ_API_KEY or GEMINI_API_KEY to your "
            ".env file (or Streamlit secrets), or run Ollama locally."
        )
        st.stop()

    model_label = st.selectbox("Model", models)
    k = st.slider("Chunks to retrieve (k)", min_value=2, max_value=10, value=5)

    st.divider()

    uploaded = st.file_uploader("Upload a PDF", type="pdf")

    if st.session_state.file_name:
        st.success(f"Loaded: {st.session_state.file_name}")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


if uploaded is not None:
    pdf_bytes = uploaded.getvalue()
    file_hash = hashlib.md5(pdf_bytes).hexdigest()

    if file_hash != st.session_state.file_hash:
        size_mb = len(pdf_bytes) / (1024 * 1024)

        if size_mb > MAX_MB:
            st.error(f"File is {size_mb:.1f} MB. The limit is {MAX_MB} MB.")
            st.stop()

        try:
            with st.spinner("Reading and indexing your PDF... this can take a while for big files."):
                st.session_state.index = build_index(pdf_bytes)
            st.session_state.file_hash = file_hash
            st.session_state.file_name = uploaded.name
            st.session_state.messages = []  # new PDF -> fresh chat
            st.rerun()
        except Exception as e:
            st.session_state.index = None
            st.session_state.file_hash = None
            st.session_state.file_name = None
            st.error(
                "Couldn't read any text from this PDF. If it's a scanned document "
                "(images of text), it needs OCR first.\n\n"
                f"Details: {e}"
            )
            st.stop()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m.get("pages"):
            st.caption("Sources: pages " + ", ".join(map(str, m["pages"])))


if st.session_state.index is None:
    st.info("👈 Upload a PDF in the sidebar to get started.")
else:
    question = st.chat_input("Ask something about the PDF")

    if question:
        # show + store the user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        # generate the answer
        with st.chat_message("assistant"):
            try:
                stream, pages = ask(
                    question,
                    st.session_state.index,
                    model_label,
                    k=k,
                )
                answer = st.write_stream(stream)
                st.caption("Sources: pages " + ", ".join(map(str, pages)))

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "pages": pages}
                )
            except Exception as e:
                st.error(f"Something went wrong while generating the answer: {e}")