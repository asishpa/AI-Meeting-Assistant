from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID  # import UUID

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    
class UserRead(BaseModel):
    user_id: UUID  # changed from id to user_id
    email: EmailStr
    full_name: str

    model_config = {
        "from_attributes": True
    }
