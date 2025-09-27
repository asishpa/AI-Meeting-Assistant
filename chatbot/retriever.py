from langchain_cohere import CohereEmbeddings
from langchain_community.vectorstores import Chroma

PERSIST_DIR = "./chroma_db"

def get_retriever(meeting_id: str):
    embeddings = CohereEmbeddings(model="large") 
    vectorstore = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
        collection_name="meetings"
    )
    return vectorstore.as_retriever(
        search_kwargs={"k": 3, "filter": {"meeting_id": meeting_id}}
    )
