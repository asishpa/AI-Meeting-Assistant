from langchain.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_template(
    """You are an expert meeting assistant.
    Answer the user's question based on the provided context from a meeting transcript.
    If the answer is not contained within the context, respond with "I don't know".

    {context}
    User Question: {question}
    """
)
    