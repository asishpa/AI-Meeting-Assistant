from langchain_cohere import CohereEmbeddings
from langchain_chroma import Chroma
from chromadb import HttpClient

def get_retriever(meeting_id: str):
    embeddings = CohereEmbeddings(model="large")

    # Connect to remote Chroma server
    client = HttpClient(host="localhost", port=8001)

    vectorstore = Chroma(
        client=client,
        collection_name="meetings",
        embedding_function=embeddings,
    )

    return vectorstore.as_retriever(
        search_kwargs={"k": 3, "filter": {"meeting_id": meeting_id}}
    )
