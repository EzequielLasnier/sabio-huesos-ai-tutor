# langchain_client.py (version 1.0 / Version token efímero)

import os
import asyncio
import pathlib
from datetime import datetime

# LangChain para RAG
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# --- Configuración de Rutas Relativas ---
BASE_DIR = pathlib.Path(__file__).parent
DATA_PATH = BASE_DIR / "data"
FAISS_DB_PATH = BASE_DIR / "faiss_index"
DOCUMENT_PATH = DATA_PATH / "anatomia_huesos.pdf"
SERVICE_ACCOUNT_FILE = BASE_DIR / "service-account-key.json"

EMBEDDING_MODEL = "models/text-embedding-004"
GENERATION_MODEL = "gemini-1.5-flash"

RAG_PROMPT_TEMPLATE = """
Eres PEPE Huesos, un asistente de voz experto en anatomía del esqueleto humano.
Tu tarea es responder preguntas estrictamente utilizando el CONTEXTO proporcionado.
Responde de forma concisa y amigable para chicos de primaria, en frases cortas para una respuesta de voz.
Si no puedes responder con el contexto, di: "Lo siento, esa información no está en mi libro de huesos."

CONTEXTO:
{context}

PREGUNTA DEL USUARIO:
{question}
"""

vector_store: FAISS = None

def initialize_worker():
    """
    Función síncrona que se ejecuta una vez cuando se inicia el proceso trabajador.
    Establece las credenciales y carga la BD FAISS en la memoria del proceso.
    """
    global vector_store
    pid = os.getpid()
    print(f"[{datetime.now()}] ⚙️ [Worker PID: {pid}] Inicializando worker RAG...", flush=True)

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(SERVICE_ACCOUNT_FILE)

    try:
        if FAISS_DB_PATH.exists():
            embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
            vector_store = FAISS.load_local(
                str(FAISS_DB_PATH),
                embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"[{datetime.now()}] ✅ [Worker PID: {pid}] Base de datos FAISS cargada.", flush=True)
        else:
            print(f"[{datetime.now()}] ⚠️ [Worker PID: {pid}] No se encontró la base de datos FAISS.", flush=True)
    except Exception as e:
        print(f"[{datetime.now()}] ❌ [Worker PID: {pid}] Error crítico al cargar la base de datos: {e}", flush=True)

async def load_and_persist_db():
    """Crea la base de datos si no existe. Solo la ejecuta el proceso principal."""
    if not DOCUMENT_PATH.exists():
        raise FileNotFoundError(f"No se encuentra el archivo PDF en: {DOCUMENT_PATH}")
    if FAISS_DB_PATH.exists() and any(FAISS_DB_PATH.iterdir()):
        return

    print(f"[{datetime.now()}] ⚠️ No se encontró base de datos FAISS. Creando una nueva desde el PDF...")

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(SERVICE_ACCOUNT_FILE)
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    loader = PyPDFLoader(str(DOCUMENT_PATH))
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(data)

    db = FAISS.from_documents(docs, embeddings)
    db.save_local(str(FAISS_DB_PATH))
    print(f"[{datetime.now()}] ✅ Base de datos FAISS creada y guardada.")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_rag_response_langchain(query: str) -> str:
    """Ejecuta la cadena RAG. Ahora se autentica automáticamente."""
    global vector_store
    
    if vector_store is None:
        return f"[{datetime.now()}] ❌ ERROR: vector_store no está inicializado en el worker."

    try:
        llm = ChatGoogleGenerativeAI(model=GENERATION_MODEL, temperature=0.3, convert_system_message_to_human=True)
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        rag_chain = (
            {"context": retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
            | prompt
            | llm
        )
        
        response = rag_chain.invoke(query)
        return response.content
        
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error al ejecutar la cadena RAG: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return "Tuve un problema al consultar mi libro de huesos."

