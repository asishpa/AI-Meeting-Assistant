from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv
from .meeting_output_schemas import MeetingSummary
from langchain.output_parsers import PydanticOutputParser
from .prompt_template import chunk_prompt, get_merge_prompt
from .utils import chunk_transcript
from langchain.chains import LLMChain
import os


load_dotenv()

# Initialize the Google Gemini Pro model
model = ChatGoogleGenerativeAI(model="gemini-pro")
summary_parser = PydanticOutputParser(pydantic_object=MeetingSummary)

##Parser part
summary_parser = PydanticOutputParser(pydantic_object=MeetingSummary)

# Pipeline part
def generate_meeting_summary(transcript_text:str) -> dict:
    """
    Full pipeline:
    1. Chunk Transcript
    2. Summarize each chunk
    3. Merge summaries into Overview, Notes, Action Items
    4. Return structured JSON dict
    """
    #Step 1: Chunk Transcript
    chunks = chunk_transcript(transcript_text)
    chunk_summaries = []

    # Step 2: Summarize each chunk
    for chunk in chunks:
        chain = LLMChain(llm=model, prompt=chunk_prompt)
        chain_summary = chain.run(transcript_chunk=chunk)
        chunk_summaries.append(chain_summary)

    # Step 3: Merge chunk summaries
    merge_prompt = get_merge_prompt(schema_json=summary_parser.get_format_instructions)
    merge_chain = LLMChain(llm=model, prompt=merge_prompt)
    merged_summary_json = merge_chain.run(
        chunk_summaries="\n".join(chunk_summaries)
    )

    # Step 4: Parse JSON
    parsed_summary = summary_parser.parse(merged_summary_json)
    return parsed_summary.model_dump()    


