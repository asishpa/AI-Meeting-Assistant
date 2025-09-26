
from fastapi import APIRouter

from app.schemas.chat_request import ChatRequest
from chatbot.chain import get_meeting_qa_chain
from starlette.responses import StreamingResponse

router = APIRouter()

@router.post("/chat")
async def chat(payload: ChatRequest):
    chain = get_meeting_qa_chain(payload.meeting_id)
    async def stream_response():
        async for event in chain.astream({"input": payload.question}):
            if "answer" in event:
                yield event["answer"]
    return StreamingResponse(stream_response(), media_type="text/event-stream")