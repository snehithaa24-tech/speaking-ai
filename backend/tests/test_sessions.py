import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check(client: httpx.AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_session_nested_config(client: httpx.AsyncClient):
    payload = {
        "config": {
            "language": "en-IN",
            "voice_name": "Kore",
            "system_instruction": "You are a helpful assistant.",
            "temperature": 0.7,
            "max_output_tokens": 2048,
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "sessionId" in data
    assert "token" in data
    assert data["status"] == "active"
    assert data["language"] == "en-IN"
    assert "startedAt" in data


@pytest.mark.asyncio
async def test_create_session_camel_case(client: httpx.AsyncClient):
    payload = {
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "आप सहायक AI हैं।",
            "temperature": 0.8,
            "maxOutputTokens": 1024,
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "sessionId" in data
    assert "token" in data
    assert data["language"] == "hi-IN"


@pytest.mark.asyncio
async def test_get_session_lifecycle(client: httpx.AsyncClient):
    # 1. Create session
    payload = {
        "config": {
            "language": "hi-IN",
            "voiceName": "Kore",
            "systemInstruction": "आप सहायक AI हैं।",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    session_id = res.json()["sessionId"]

    # 2. Get session
    get_res = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    session_data = get_res.json()
    assert session_data["id"] == session_id
    assert session_data["status"] == "active"
    assert session_data["language"] == "hi-IN"

    # 3. End session
    end_res = await client.delete(f"/api/v1/sessions/{session_id}")
    assert end_res.status_code == 204

    # 4. Verify ended
    get_res2 = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_res2.status_code == 200
    assert get_res2.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_get_nonexistent_session(client: httpx.AsyncClient):
    res = await client.get("/api/v1/sessions/non-existent-uuid")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_submit_feedback(client: httpx.AsyncClient):
    # Create session first
    create_res = await client.post("/api/v1/sessions", json={
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Test instruction",
        }
    })
    session_id = create_res.json()["sessionId"]

    # Submit feedback
    feedback_payload = {
        "sessionId": session_id,
        "rating": 5,
        "comment": "Excellent accessibility experience!",
    }
    fb_res = await client.post("/api/v1/feedback", json=feedback_payload)
    assert fb_res.status_code == 201
    fb_data = fb_res.json()
    assert fb_data["sessionId"] == session_id
    assert fb_data["rating"] == 5
    assert fb_data["comment"] == "Excellent accessibility experience!"


@pytest.mark.asyncio
async def test_submit_feedback_nonexistent_session(client: httpx.AsyncClient):
    fb_payload = {
        "sessionId": "00000000-0000-0000-0000-000000000000",
        "rating": 3,
        "comment": "Session not found test",
    }
    res = await client.post("/api/v1/feedback", json=fb_payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_session_unsupported_language(client: httpx.AsyncClient):
    payload = {
        "config": {
            "language": "fr-FR",
            "voiceName": "Kore",
            "systemInstruction": "Test unsupported language.",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_session_with_auth_header(client: httpx.AsyncClient, db_session):
    """Session created with Authorization header links the authenticated user's ID."""
    from app.services.auth import AuthService

    auth_service = AuthService(db_session)
    user = await auth_service.get_or_create_user({
        "email": "session_user@sahayak.ai",
        "name": "Session User",
    })
    token = auth_service.create_access_token(user)

    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Authenticated user session test.",
        }
    }
    res = await client.post(
        "/api/v1/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    session_id = res.json()["sessionId"]

    get_res = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    session_data = get_res.json()
    user_id_field = session_data.get("userId") or session_data.get("user_id")
    assert user_id_field == user.id


@pytest.mark.asyncio
async def test_create_session_anonymous(client: httpx.AsyncClient):
    """Session created without Authorization header has user_id == None."""
    payload = {
        "config": {
            "language": "en-IN",
            "voiceName": "Kore",
            "systemInstruction": "Anonymous user session test.",
        }
    }
    res = await client.post("/api/v1/sessions", json=payload)
    assert res.status_code == 201
    session_id = res.json()["sessionId"]

    get_res = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    session_data = get_res.json()
    user_id_field = session_data.get("userId") or session_data.get("user_id")
    assert user_id_field is None



