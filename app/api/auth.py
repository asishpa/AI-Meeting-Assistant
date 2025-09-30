from fastapi import APIRouter, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreate, UserRead, UserLogin
from app.services.auth.auth import signup_user, login_user
from app.db.session import get_db  # Sync session
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await signup_user(
        session=db,
        full_name=user_data.full_name,
        email=user_data.email,
        password=user_data.password,
    )


@router.post("/login", response_model=UserRead)
async def login(
    user_data: UserLogin,
    response: Response,  # <- FastAPI automatically injects this
    db: AsyncSession = Depends(get_db)
):
    user = await login_user(
        session=db,
        email=user_data.email,
        password=user_data.password,
    )

    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.user_id), "email": user.email}
    )

    # Add token to headers
    response.headers["Authorization"] = f"Bearer {access_token}"

    # Return user details in body
    return {
        "user_id": str(user.user_id),
        "full_name": user.full_name,
        "email": user.email
    }
