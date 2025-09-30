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
    MEETING_NOT_FOUND = "MEETING_001"
    MEETING_ACCESS_DENIED = "MEETING_002"
    NO_MEETINGS_FOUND = "MEETING_003"

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
class MeetingError(HTTPException):
    """ Custom exception for meeting-related failures """
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
# Auth error messages for authentication failures
class AuthErrorMessages:
    """ Error messages for authentication failures """
    UNAUTHENTICATED_USER = "User is not authenticated. Please provide a valid token."
    INVALID_TOKEN = "Invalid or expired token. Please login again."
    USER_NOT_FOUND = "Authenticated user not found."

# Signup error messages for signup failures
class SignupErrorMessages:
    """ Error messages for signup failures """
    USER_NOT_FOUND = "User not found"
    INVALID_CREDENTIALS = "Invalid credentials"
    EMAIL_ALREADY_EXISTS = "Email already exists"
class MeetingErrorMessages:
    """ Error messages for meeting-related failures """
    MEETING_NOT_FOUND = "Meeting not found"
    MEETING_ACCESS_DENIED = "Access to the meeting is denied"
    NO_MEETINGS_FOUND = "No meetings found for the user"
# convenience functions for common signup errors
def raise_invalid_credentials():
    error_info = SignupErrorMessages.INVALID_CREDENTIALS
    raise SignupError(
        error_code=ErrorCode.INVALID_CREDENTIALS,
        message=error_info,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
