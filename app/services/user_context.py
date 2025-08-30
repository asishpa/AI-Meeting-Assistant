from fastapi import Request,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from app.models.user import User
from app.db.session import get_db  # Sync session
from app.utils.security import verify_access_token
from app.core.errors import AuthError, ErrorCode, AuthErrorMessages

async def get_current_user(
        request: Request,
        session: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current user from the request.
    Args:
        request (Request): The FastAPI request object.
        session (AsyncSession): The database session.
    Returns:
        Optional[User]: The current user if authenticated, None otherwise.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError(
            error_code=ErrorCode.UNAUTHENTICATED_USER,
            message=AuthErrorMessages.UNAUTHENTICATED_USER,
            status_code=401
        )

    token = auth_header.split(" ")[1]
    payload = verify_access_token(token)
    if not payload:
        raise AuthError(
            error_code=ErrorCode.UNAUTHENTICATED_USER,
            message=AuthErrorMessages.UNAUTHENTICATED_USER,
            status_code=401
        )

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError(
            error_code=ErrorCode.UNAUTHENTICATED_USER,
            message=AuthErrorMessages.UNAUTHENTICATED_USER,
            status_code=401
        )

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalars().first()