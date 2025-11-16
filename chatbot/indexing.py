from langchain_cohere import CohereEmbeddings
from langchain_chroma import Chroma
from chromadb import HttpClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY not found in environment variables")

# Embeddings
embeddings = CohereEmbeddings(model="large")

# Remote Chroma client
client = HttpClient(host="chroma", port=8000)

def index_meeting(meeting_id: str, transcript_text: str, metadata: dict = None):
    # Split transcript
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript_text)

    # Prepare documents
    docs = [
        Document(
            page_content=chunk,
            metadata={**(metadata or {}), "meeting_id": meeting_id, "chunk_index": idx}
        )
        for idx, chunk in enumerate(chunks)
    ]

    # Upload to remote Chroma collection
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="meetings",
        client=client  # IMPORTANT: remote Chroma
    )

    return vectorstore
