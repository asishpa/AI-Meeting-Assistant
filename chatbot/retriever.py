from langchain.embeddings import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import Chroma


PERSIST_DIR= "./chroma_db"
def get_retriever(meeting_id: str):
    embeddings = GoogleGenerativeAIEmbeddings(model = "models/embedding-001")
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 3, "filter": {"meeting_id": meeting_id}})