from unittest import result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID as UUIDType
from app.models.meeting import Meeting
from app.schemas.meet import MeetingMetadataDetails,MeetingDetails
from app.utils.s3 import generate_presigned_url,S3_BUCKET
from app.core.errors import MeetingError, MeetingErrorMessages, ErrorCode
from fastapi import status
class MeetingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_meetings(self, user_id: UUIDType) -> List[MeetingMetadataDetails]:
        result = await self.db.execute(
            select(Meeting).where(Meeting.user_id == user_id)
            .order_by(Meeting.start_time.desc())
        )
        meetings = result.scalars().all()
        if not meetings:
            raise MeetingError(
                error_code=ErrorCode.NO_MEETINGS_FOUND,
                message=MeetingErrorMessages.NO_MEETINGS_FOUND,
                status_code=status.HTTP_200_OK
            )
        return [MeetingMetadataDetails.model_validate(m) for m in meetings]
    async def get_meeting(self, meeting_id: UUIDType, user_id: UUIDType) -> MeetingDetails:
    
        result = await self.db.execute(
            select(Meeting).where(Meeting.id==meeting_id,Meeting.user_id == user_id)
        )
        meeting = result.scalars().first()
        if not meeting:
            raise MeetingError(
                error_code=ErrorCode.MEETING_NOT_FOUND,
                message=MeetingErrorMessages.MEETING_NOT_FOUND,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        audio_url = generate_presigned_url(S3_BUCKET, meeting.audio_object)
        meeting_data = MeetingDetails.model_validate(meeting)
        meeting_data.audio_url = audio_url
        return meeting_data
