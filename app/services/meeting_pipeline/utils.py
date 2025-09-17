
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_transcript(transcript_text:str, chunk_size=1000,chunk_overlap=100):
    """
    Split a large transcript text into smaller chunks for processing.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap)
    return splitter.split_text(transcript_text)