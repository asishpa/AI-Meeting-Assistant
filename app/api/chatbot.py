from fastapi import APIRouter
from app.schemas.chat_request import ChatRequest
from chatbot.chain import get_meeting_qa_chain
from starlette.responses import StreamingResponse
import asyncio
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

router = APIRouter()

@router.post("/chat")
async def chat(payload: ChatRequest):
    logger.debug(f"Received request: meeting_id={payload.meeting_id}, question={payload.question}")
    chain = get_meeting_qa_chain(payload.meeting_id)

    async def stream_response():
        logger.debug("Starting stream_response generator")
        async for event in chain.astream(payload.question):
            logger.debug(f"Got event from chain.astream: {event}")
            if "answer" in event:
                answer = event["answer"]
                logger.debug(f"Yielding answer: {answer}")
                # Use proper SSE format to flush to client
                yield f"data: {answer}\n\n"
            else:
                logger.debug("Event has no 'answer' key")
        logger.debug("Finished streaming")

    return StreamingResponse(stream_response(), media_type="text/event-stream")
