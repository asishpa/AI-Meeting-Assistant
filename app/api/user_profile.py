from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.db.session import get_db  # Sync session
from app.services.user_context import get_current_user
from app.schemas.user import UserRead

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the details of the currently authenticated user.
    """
    # The current_user object is an instance of your SQLAlchemy User model
    return current_user
