import os
from datetime import datetime, timedelta, timezone
from typing import Union, Any
from jose import jwt
import bcrypt

def hash_password(password: str) -> str:
    """
    Hash a plain password using bcrypt.
    Args:
        password (str): The plain password to hash.
    Returns:
        str: The hashed password.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hashed version.
    Args:
        plain_password (str): The plain password to verify.
        hashed_password (str): The hashed password to compare against.
    Returns:
        bool: True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token.
    Args:
        data (dict): The data to encode in the token.
        expires_delta (timedelta): Optional expiration time delta.
    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.getenv("JWT_SECRET_KEY"), algorithm="HS256")

def verify_access_token(token: str) -> Union[dict, None]:
    """
    Verify a JWT access token and return the decoded payload if valid.
    Args:
        token (str): The JWT token to verify.
    Returns:
        dict: The decoded token data if valid.
        None: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY"),
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        return payload
    except Exception:
        return None