import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.utils.security import hash_password, verify_password
from app.core.errors import SignupError, SignupErrorMessages, ErrorCode
from fastapi import status

# Async signup function
async def signup_user(session: AsyncSession, full_name: str, email: str, password: str) -> User:
    # Check if user already exists
    result = await session.execute(
        select(User).where((User.full_name == full_name) | (User.email == email))
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise SignupError(
            error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            message=SignupErrorMessages.EMAIL_ALREADY_EXISTS,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Hash password
    hashed_password = hash_password(password)
    
    # Create new user (UUID generated automatically)
    new_user = User(
        full_name=full_name,
        email=email,
        password=hashed_password
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user



# Async login function
async def login_user(session: AsyncSession, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise SignupError(
            error_code=ErrorCode.USER_NOT_FOUND,
            message=SignupErrorMessages.USER_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    if not verify_password(password, user.password):
        raise SignupError(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message=SignupErrorMessages.INVALID_CREDENTIALS,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return user
