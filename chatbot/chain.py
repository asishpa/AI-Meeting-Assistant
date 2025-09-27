
from chatbot.prompt_template import prompt
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from chatbot.retriever import get_retriever


load_dotenv()

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash",streaming=True)

def get_meeting_qa_chain(meeting_id: str):
    retriever = get_retriever(meeting_id)

    combine_docs_chain = create_stuff_documents_chain(model,prompt)
    return retriever | combine_docs_chain



