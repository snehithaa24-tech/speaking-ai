"""
backend/tests/test_language.py
Complete verification test suite for Milestone 2:
- Strict Two-Language Support (en-IN and hi-IN)
- 422 Unprocessable Entity enforcement for te-IN and invalid language codes
- Knowledge search tool schema and document seed verification (Zero Telugu)
"""

import pytest
import httpx
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.schemas import LanguageCode, VoiceSessionConfig
from app.services.gemini_live import gemini_live_service
from app.services.knowledge import KnowledgeService
from app.models.models import KnowledgeDocument


# ==========================================
# 1. Schema & Enum Strictness Tests
# ==========================================

def test_language_code_enum_strictly_two_options():
    """Verify LanguageCode enum contains strictly en-IN and hi-IN and NO te-IN."""
    codes = [e.value for e in LanguageCode]
    assert sorted(codes) == ["en-IN", "hi-IN"]
    assert len(LanguageCode) == 2
    assert hasattr(LanguageCode, "EN_IN")
    assert hasattr(LanguageCode, "HI_IN")
    assert not hasattr(LanguageCode, "TE_IN")


def test_gemini_live_tool_declarations_strict_languages():
    """Verify search_knowledge tool declaration enum in Gemini Live has strictly en-IN and hi-IN."""
    tools = gemini_live_service.get_live_tools()
    assert len(tools) > 0
    search_tool = None
    for tool in tools:
        for decl in tool.function_declarations:
            if decl.name == "search_knowledge":
                search_tool = decl
                break
    assert search_tool is not None, "search_knowledge tool not declared in live tools"

    # Check language parameter schema
    lang_prop = search_tool.parameters.properties.get("language")
    assert lang_prop is not None
    assert sorted(lang_prop.enum) == ["en-IN", "hi-IN"]
    assert "te-IN" not in lang_prop.enum

    # Check query description does not mention Telugu
    query_desc = search_tool.parameters.properties["query"].description
    assert "Telugu" not in query_desc


def test_gemini_live_system_instructions():
    """Verify system instructions and greetings only support English and Hindi."""
    en_inst = gemini_live_service.get_system_instruction(LanguageCode.EN_IN)
    hi_inst = gemini_live_service.get_system_instruction(LanguageCode.HI_IN)
    assert "Sahayak AI" in en_inst
    assert "सहायक AI" in hi_inst

    # Voice mapping checks
    assert gemini_live_service.get_voice_for_language(LanguageCode.EN_IN) == "Kore"
    assert gemini_live_service.get_voice_for_language(LanguageCode.HI_IN) == "Kore"


# ==========================================
# 2. Session Creation Multilingual Validation Tests
# ==========================================

@pytest.mark.asyncio
async def test_session_create_valid_english(client: httpx.AsyncClient):
    """POST /api/v1/sessions with en-IN should return 201 Created."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "You are a helpful voice assistant.",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["language"] == "en-IN"
    assert data["status"] == "active"
    assert "sessionId" in data
    assert "token" in data


@pytest.mark.asyncio
async def test_session_create_valid_hindi(client: httpx.AsyncClient):
    """POST /api/v1/sessions with hi-IN should return 201 Created."""
    payload = {
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "आप एक सहायक वॉयस असिस्टेंट हैं।",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["language"] == "hi-IN"
    assert data["status"] == "active"
    assert "sessionId" in data
    assert "token" in data


@pytest.mark.asyncio
async def test_session_create_rejection_telugu(client: httpx.AsyncClient):
    """POST /api/v1/sessions with te-IN MUST return 422 Unprocessable Entity."""
    payload = {
        "config": {
            "language": "te-IN",
            "voiceName": "Kore",
            "systemInstruction": "మీరు సహాయక్ AI.",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 422
    err_detail = res.json()["detail"]
    assert any("language" in str(err["loc"]) for err in err_detail)


@pytest.mark.parametrize("invalid_lang", [
    "ta-IN",
    "kn-IN",
    "ml-IN",
    "bn-IN",
    "fr-FR",
    "es-ES",
    "en-US",
    "invalid-string",
    "",
])
@pytest.mark.asyncio
async def test_session_create_rejection_invalid_languages(client: httpx.AsyncClient, invalid_lang: str):
    """POST /api/v1/sessions with any unsupported language code MUST return 422."""
    payload = {
        "config": {
            "language": invalid_lang,
            "voiceName": "Kore",
            "systemInstruction": "Test instruction",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 422


# ==========================================
# 3. Knowledge Base Multilingual & Seed Purge Tests
# ==========================================

@pytest.mark.asyncio
async def test_knowledge_search_valid_languages(client: httpx.AsyncClient):
    """POST /api/v1/knowledge/search accepts en-IN and hi-IN."""
    en_search = await client.post("/api/v1/knowledge/search", json={
        "query": "farmer scheme",
        "language": "en-IN",
    })
    assert en_search.status_code == 200

    hi_search = await client.post("/api/v1/knowledge/search", json={
        "query": "किसान योजना",
        "language": "hi-IN",
    })
    assert hi_search.status_code == 200


@pytest.mark.asyncio
async def test_knowledge_search_telugu_rejected(client: httpx.AsyncClient):
    """POST /api/v1/knowledge/search with te-IN MUST return 422."""
    te_search = await client.post("/api/v1/knowledge/search", json={
        "query": "పథకం",
        "language": "te-IN",
    })
    assert te_search.status_code == 422


@pytest.mark.asyncio
async def test_knowledge_create_document_telugu_rejected(client: httpx.AsyncClient):
    """POST /api/v1/knowledge with te-IN MUST return 422."""
    payload = {
        "title": "రైతు భరోసా",
        "category": "government_schemes",
        "content": "రైతులకు ఆర్థిక సహాయం అందించే పథకం.",
        "language": "te-IN",
    }
    res = await client.post("/api/v1/knowledge", json=payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_seed_initial_data_contains_zero_telugu(db_session: AsyncSession):
    """Verify that seed_initial_data only inserts en-IN and hi-IN documents, with zero Telugu."""
    service = KnowledgeService(db_session)
    await service.seed_initial_data()

    # Query all seeded documents
    result = await db_session.execute(select(KnowledgeDocument))
    docs = result.scalars().all()
    assert len(docs) > 0

    telugu_regex = re.compile(r"[\u0C00-\u0C7F]")  # Unicode block for Telugu

    for doc in docs:
        assert doc.language in ["en-IN", "hi-IN"], f"Document {doc.id} has invalid language {doc.language}"
        assert doc.language != "te-IN"
        # Assert no Telugu script in title or content
        assert not telugu_regex.search(doc.title), f"Document {doc.id} contains Telugu script in title: {doc.title}"
        assert not telugu_regex.search(doc.content), f"Document {doc.id} contains Telugu script in content: {doc.content[:50]}"
