import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

models = {
    "GPT-OSS 120B (Groq)":  {"provider": "groq",   "model": "openai/gpt-oss-120b"},
    "GPT-OSS 20B (Groq)":   {"provider": "groq",   "model": "openai/gpt-oss-20b"},
    "Gemini 3.5 Flash":     {"provider": "gemini", "model": "gemini-3.5-flash"},
    "Gemini 3.1 Flash-Lite":{"provider": "gemini", "model": "gemini-3.1-flash-lite"}
}

keys={
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

def available_models():
    """Only list models whose API key is set, so the dropdown never offers a dead option."""
    out = []
    for label, cfg in models.items():
        key = keys[cfg["provider"]]
        if key is None or os.getenv(key):
            out.append(label)
    return out

def get_model(name):
    detail=models[name]
    provider=detail["provider"]
    model=detail["model"]

    if provider=="groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, temperature=0)
    if provider=="gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model,google_api_key=os.getenv("GEMINI_API_KEY"), temperature=0)
    if provider=="ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, temperature=0)
    raise ValueError(f"Unknown provider {provider} for model {name}")

prompt=ChatPromptTemplate.from_template("""
You are great at reading PDF and a professional at answering questions from the content of the PDF. 
You will be given a question and a context. 
The context is extracted from a PDF document. 
Your task is to provide a concise and accurate answer to the question based on the information available in the context. 
If the answer is not present in the context, please respond with "I don't know."

Context: {context}
Question: {question}
""")

def format_docs(docs):
    out = []
    for d in docs:
        out.append(f"Page {d.metadata['page']}:\n{d.page_content}\n")
    return "\n".join(out)   

def ask(question, index, model_label, k=5):
    docs = index.similarity_search(question, k=k)
    pages = sorted({d.metadata["page"] for d in docs})

    chain = prompt | get_model(model_label) | StrOutputParser()
    stream = chain.stream({
        "context": format_docs(docs),
        "question": question
    })
    return stream, pages

#chain.invoke({...})   # waits, returns the full answer as one string
#chain.stream({...})   # yields "The", " document", " says", ... as they arrive