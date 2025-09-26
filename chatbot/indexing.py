from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import Chroma

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document

PERSIST_DIR ="./chroma_db"
embeddings = GoogleGenerativeAIEmbeddings(model = "models/embedding-001")
def index_meeting(meeting_id: str, transcript_text: str, metadata: dict = None):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript_text)
    docs = [
        Document(
            page_content=chunk,
            metadata={**(metadata or {}), "meeting_id": meeting_id, "chunk_index": idx}
        )
        for idx, chunk in enumerate(chunks)
    ]
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name="meetings"
    )
    vectorstore.persist()
    return vectorstore