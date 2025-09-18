from langchain.prompts import ChatPromptTemplate

chunk_prompt = ChatPromptTemplate.from_template(
    """You are an expert meeting assistant.
    Summarize the following transcript chunk into concise notes.
    Include:
    - Timestamps
    - Speaker names
    - Bullet points for actions or important points

    Transcript chunk:
    {transcript_chunk}
    """
)

merge_prompt = ChatPromptTemplate.from_template(
    """You are an expert meeting assistant.
    You have the following chunk summaries. Merge them into a full meeting summary.

    Provide:
    - Overview: One concise paragraph summarizing the key points.
    - Notes: Group by topic or agenda time, include start_time and end_time, and speaker names in bullet points.
    - Action Items: Extract tasks, group by assignee if possible, and include timestamps if available.

    Chunk Summaries:
    {chunk_summaries}
    """
)
