import os
import re
import logging
from typing import Dict
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Load API key
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GOOGLE_API_KEY environment variable not set.")
    raise RuntimeError("GOOGLE_API_KEY environment variable not set.")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

def clean_gemini_text(text: str) -> str:
    """
    Clean Gemini model output for speech or display.
    Removes markdown syntax, bullets, and excessive whitespace.
    """
    if not text:
        return ""
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"^[\s•\-]+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

def query_gemini_search(question: str) -> Dict[str, str]:
    """
    Send a question to Google Gemini AI (with Search grounding)
    and return a structured, cleaned response.
    Returns dict: {"success": bool, "answer": str, "error": str}
    """
    try:
        # Enable Google Search grounding
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        # Query the Gemini model
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=question,
            config=config,
        )

        # Extract text safely
        answer = ""
        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            answer += part["text"] + "\n"

        # Clean the text
        answer = clean_gemini_text(answer)

        return {"success": True, "answer": answer or "No response text found.", "error": ""}

    except Exception as e:
        logger.error(f"Gemini Search API request failed: {e}")
        return {"success": False, "answer": "", "error": str(e)}
