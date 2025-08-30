from fastapi import APIRouter
from app.api import auth, meetings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(meetings.router)
