from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


class LanguageCode(str, Enum):
    EN_IN = "en-IN"
    HI_IN = "hi-IN"


class KnowledgeCategory(str, Enum):
    AGRICULTURE = "agriculture"
    GOVERNMENT_SCHEMES = "government_schemes"
    TRANSPORT = "transport"
    HOSPITAL_ASSISTANCE = "hospital_assistance"
    GENERAL = "general"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    INTERRUPTED = "interrupted"


class SpeakerType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class EvaluationResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class VoiceSessionConfig(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    language: LanguageCode = LanguageCode.EN_IN
    voice_name: str = "Kore"
    system_instruction: str
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=2048, ge=1, le=8192)


class SessionCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    config: VoiceSessionConfig
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    session_id: str
    token: str
    status: SessionStatus = SessionStatus.ACTIVE
    language: LanguageCode
    started_at: datetime


class SessionInfo(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str
    user_id: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    status: SessionStatus
    language: LanguageCode
    message_count: int


class ConversationMessage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str
    session_id: str
    speaker: SpeakerType
    transcript: str
    language: LanguageCode
    is_final: bool
    timestamp: datetime
    meta: Optional[Dict[str, Any]] = None


class KnowledgeDocumentBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str = Field(min_length=1, max_length=500)
    category: KnowledgeCategory
    source_url: Optional[HttpUrl] = None
    content: str = Field(min_length=1)
    language: LanguageCode = LanguageCode.EN_IN
    published_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    pass


class KnowledgeDocumentUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    category: Optional[KnowledgeCategory] = None
    source_url: Optional[HttpUrl] = None
    content: Optional[str] = Field(default=None, min_length=1)
    language: Optional[LanguageCode] = None
    published_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None


class KnowledgeDocumentResponse(KnowledgeDocumentBase):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    query: str = Field(min_length=1, max_length=500)
    category: Optional[KnowledgeCategory] = None
    language: Optional[LanguageCode] = None
    limit: int = Field(default=10, ge=1, le=50)


class KnowledgeSearchResult(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    documents: List[KnowledgeDocumentResponse]
    query: str
    language: Optional[LanguageCode]
    total_results: int


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    session_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str
    session_id: str
    rating: int
    comment: Optional[str]
    created_at: datetime


class EvaluationRecordCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    language: LanguageCode
    test_category: str = Field(min_length=1, max_length=100)
    result: EvaluationResult
    measured_latency: Optional[int] = Field(default=None, ge=0)
    word_error_rate: Optional[int] = Field(default=None, ge=0, le=100)
    notes: Optional[str] = Field(default=None, max_length=1000)


class EvaluationRecordResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str
    language: LanguageCode
    test_category: str
    result: EvaluationResult
    measured_latency: Optional[int]
    word_error_rate: Optional[int]
    notes: Optional[str]
    created_at: datetime


class GoogleAuthRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: str
    redirect_uri: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: str
    email: EmailStr
    name: str
    picture: Optional[str]
    preferred_language: LanguageCode
    created_at: datetime


class ErrorResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    status: str
    version: str
    timestamp: datetime