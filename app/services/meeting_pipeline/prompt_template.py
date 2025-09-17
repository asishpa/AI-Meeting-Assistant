from langchain.prompts import ChatPromptTemplate
from .meeting_output_schemas import MeetingSummary

chunk_prompt = ChatPromptTemplate.from_template(
    """You are an expert meeting assistant.
    Summarzie the following transcript chunk into concise notes.
    Include:
    - Timestamps
    - Speaker names
    - Bullet points for actions or important points

    Transcript chunk:
    {transcript_chunk}
    """)
merge_prompt_template = """
    You are an expert meeting assistant.
    You have the following chunk summaries .Merge them into a full meeting summary 
    Overview:
    - One concise paragraph summarizing the key points.
    Notes:
    - Group by topic or agenda time
    - Include start_time and end_time for each topic
    - Include speaker names in bullet points
    Action Items:
    - Extract tasks
    - Group by assignne if possible
    - Include timestamps if possible
    Output STRICTLY in JSON matching this schema:
    {schema_json}
    Chunk Summaries:
    {chunk_summaries}
    """
def get_merge_prompt(schema_json: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_template(
        merge_prompt_template.format(schema_json=schema_json)
    )