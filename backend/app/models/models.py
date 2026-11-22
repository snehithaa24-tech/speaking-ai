from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Enum as SQLEnum, Index, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.session import Base
import enum
import uuid


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class SpeakerType(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class KnowledgeCategory(str, enum.Enum):
    AGRICULTURE = "agriculture"
    GOVERNMENT_SCHEMES = "government_schemes"
    TRANSPORT = "transport"
    HOSPITAL_ASSISTANCE = "hospital_assistance"
    GENERAL = "general"


class EvaluationResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    picture = Column(String(500), nullable=True)
    preferred_language = Column(String(10), default="en-IN", nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    language = Column(String(10), default="en-IN", nullable=False)
    message_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sessions_user_started", "user_id", "started_at"),
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    speaker = Column(SQLEnum(SpeakerType), nullable=False)
    transcript = Column(Text, nullable=False)
    language = Column(String(10), default="en-IN", nullable=False)
    is_final = Column(Boolean, default=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)

    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_timestamp", "session_id", "timestamp"),
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="feedback")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    category = Column(SQLEnum(KnowledgeCategory), nullable=False, index=True)
    source_url = Column(String(1000), nullable=True)
    content = Column(Text, nullable=False)
    language = Column(String(10), default="en-IN", nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_knowledge_category_language", "category", "language"),
    )


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    language = Column(String(10), nullable=False, index=True)
    test_category = Column(String(100), nullable=False)
    result = Column(SQLEnum(EvaluationResult), nullable=False)
    measured_latency = Column(Integer, nullable=True)
    word_error_rate = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_evaluation_language_category", "language", "test_category"),
    )