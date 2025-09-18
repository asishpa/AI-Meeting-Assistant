from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from .meeting_output_schemas import MeetingSummary
from .prompt_template import chunk_prompt, merge_prompt
from .utils import chunk_transcript

load_dotenv()

# Initialize the Google Gemini Pro model
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Wrap model to enforce structured output with MeetingSummary
structured_model = model.with_structured_output(MeetingSummary)


def generate_meeting_summary(transcript_text: str) -> dict:
    """
    Full pipeline:
    1. Chunk Transcript
    2. Summarize each chunk
    3. Merge summaries into Overview, Notes, Action Items
    4. Return structured JSON dict
    """
    # Step 1: Chunk Transcript
    chunks = chunk_transcript(transcript_text)
    chunk_summaries = []

    # Step 2: Summarize each chunk
    chunk_chain = chunk_prompt | model
    for chunk in chunks:
        summary = chunk_chain.invoke({"transcript_chunk": chunk})
        chunk_summaries.append(summary.content)

    # Step 3: Merge chunk summaries into structured output
    merge_chain = merge_prompt | structured_model
    merged_summary = merge_chain.invoke({"chunk_summaries": "\n".join(chunk_summaries)})

    # Step 4: Return dict (Pydantic model → dict)
    return merged_summary.model_dump()
