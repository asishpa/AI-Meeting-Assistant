from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.errors import SignupError
import logging

logger = logging.getLogger(__name__)

async def signup_error_handler(request: Request, exc: SignupError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

async def generic_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later."
        },
    )
