import fitz
from langchain_core.documents import Document

def load_pdf(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [
        Document(page_content=p.get_text(), metadata={"page": i})
        for i, p in enumerate(doc, start=1)
        if p.get_text().strip()
    ]