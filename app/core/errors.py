from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from enum import Enum

class ErrorCode(str, Enum):
    """ Standard error codes for the application. """
    USER_NOT_FOUND = "AUTH__001"
    INVALID_CREDENTIALS = "AUTH_002"
    EMAIL_ALREADY_EXISTS = "AUTH_003"
    UNAUTHENTICATED_USER = "AUTH_004"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_001"

class SignupError(HTTPException):
    """ Custom exception in case of signup failure """
    def __init__(
            self,
            error_code: ErrorCode,
            message: str,
            status_code: int = status.HTTP_400_BAD_REQUEST,
            details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(status_code=status_code, detail={
            "error_code": self.error_code,
            "message": message,
            "details": self.details
        })
class TranscriptionError(HTTPException):
    """ Custom exception for transcription failures """
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail={
            "error_code": ErrorCode.TRANSCRIPTION_FAILED,
            "message": message
        })

class AuthError(HTTPException):
    """ Custom exception in case of authentication failure """
    def __init__(
            self,
            error_code: ErrorCode,
            message: str,
            status_code: int = status.HTTP_401_UNAUTHORIZED,
            details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(status_code=status_code, detail={
            "error_code": self.error_code,
            "message": message,
            "details": self.details
        })
class SignupErrorMessages:
    """ Error messages for signup failures """
    USER_NOT_FOUND = "User not found"
    INVALID_CREDENTIALS = "Invalid credentials"
    EMAIL_ALREADY_EXISTS = "Email already exists"
# convenience functions for common signup errors
def raise_invalid_credentials():
    error_info = SignupErrorMessages.INVALID_CREDENTIALS
    raise SignupError(
        error_code=ErrorCode.INVALID_CREDENTIALS,
        message=error_info,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
