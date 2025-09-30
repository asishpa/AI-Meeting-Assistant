from langchain_cohere import CohereEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

PERSIST_DIR = "./chroma_db"

# Read Cohere API key from environment
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY not found in environment variables")

# Initialize Cohere embeddings
embeddings = CohereEmbeddings(model="large")

def index_meeting(meeting_id: str, transcript_text: str, metadata: dict = None):
    # Split transcript into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript_text)

    # Create Document objects
    docs = [
        Document(
            page_content=chunk,
            metadata={**(metadata or {}), "meeting_id": meeting_id, "chunk_index": idx}
        )
        for idx, chunk in enumerate(chunks)
    ]

    # Create and persist Chroma vector store
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name="meetings"
    )
    vectorstore.persist()
    return vectorstore
