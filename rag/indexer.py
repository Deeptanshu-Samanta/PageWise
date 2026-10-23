from langchain_community.vectorstores import FAISS
from .parser import load_pdf
from .chunker import split_docs
# remove: from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

embedding = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_index(pdf_bytes: bytes):
    chunks = split_docs(load_pdf(pdf_bytes))
    return FAISS.from_documents(chunks, embedding)
