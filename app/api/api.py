from fastapi import APIRouter
from app.api import auth, chatbot, meetings,user_profile

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(meetings.router)
api_router.include_router(user_profile.router)
api_router.include_router(chatbot.router)
