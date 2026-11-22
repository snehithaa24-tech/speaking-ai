from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.schemas.schemas import (
    SessionCreate,
    SessionResponse,
    SessionInfo,
    ErrorResponse,
    VoiceSessionConfig,
    FeedbackCreate,
    FeedbackResponse,
    ConversationMessage as ConversationMessageSchema,
)
from app.services.gemini_live import gemini_live_service
from app.services.auth import get_optional_current_user
from app.models.models import Session, SessionStatus, Feedback, ConversationMessage, User
import uuid


router = APIRouter()


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_session(
    # Accept both { config: VoiceSessionConfig } and direct VoiceSessionConfig for compatibility
    session_create: SessionCreate | VoiceSessionConfig = Body(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Handle both request formats and extract user_id if authenticated
        if isinstance(session_create, SessionCreate):
            config = session_create.config
            user_id = session_create.user_id
        else:
            config = session_create
            user_id = None

        if current_user:
            user_id = current_user.id

        session_id = str(uuid.uuid4())
        token = gemini_live_service.create_session_token(session_id, config, user_id=user_id)

        db_session = Session(
            id=session_id,
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            language=config.language.value,
        )
        db.add(db_session)
        await db.commit()

        return SessionResponse(
            session_id=session_id,
            token=token,
            status=SessionStatus.ACTIVE,
            language=config.language,
            started_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionInfo,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return SessionInfo(
        id=session.id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        language=session.language,
        message_count=session.message_count,
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == feedback.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    db_feedback = Feedback(
        id=str(uuid.uuid4()),
        session_id=feedback.session_id,
        rating=feedback.rating,
        comment=feedback.comment,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_feedback)
    await db.commit()
    await db.refresh(db_feedback)
    return FeedbackResponse.model_validate(db_feedback)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ConversationMessageSchema],
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    msg_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.timestamp)
    )
    messages = msg_result.scalars().all()
    return [ConversationMessageSchema.model_validate(m) for m in messages]
