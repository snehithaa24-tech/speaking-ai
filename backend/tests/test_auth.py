import pytest
from httpx import AsyncClient
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_auth_me_unauthorized(client: AsyncClient):
    """GET /api/v1/auth/me without token should return 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_invalid_token(client: AsyncClient):
    """GET /api/v1/auth/me with invalid token should return 401."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_value"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_google_invalid_code(client: AsyncClient):
    """POST /api/v1/auth/google with unverified code should return 401 Unauthorized."""
    payload = {
        "code": "invalid_mock_auth_code_12345",
        "redirectUri": "http://localhost:5173/auth/callback",
    }
    response = await client.post("/api/v1/auth/google", json=payload)
    assert response.status_code == 401
    assert "Invalid Google token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auth_google_invalid_payload(client: AsyncClient):
    """POST /api/v1/auth/google with missing fields should return 422."""
    response = await client.post("/api/v1/auth/google", json={"invalid": "payload"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_token_creation_and_auth_me_lifecycle(client: AsyncClient, db_session):
    """Verify that a created user can generate an access token and authenticate to /auth/me."""
    auth_service = AuthService(db_session)
    user_data = {
        "email": "testuser@sahayak.ai",
        "name": "Sahayak Test User",
        "picture": "https://example.com/avatar.png",
    }
    user = await auth_service.get_or_create_user(user_data)
    assert user.id is not None
    assert user.email == "testuser@sahayak.ai"

    # Create access token
    token = auth_service.create_access_token(user)
    assert isinstance(token, str)

    # Call /api/v1/auth/me with the token
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@sahayak.ai"
    assert data["name"] == "Sahayak Test User"


@pytest.mark.asyncio
async def test_google_oauth_valid_token_success(client: AsyncClient):
    """Valid Google ID token returns 200 with bearer access token."""
    from unittest.mock import patch
    from app.core.config import settings

    mock_id_info = {
        "sub": "google-user-998877",
        "email": "googleuser@sahayak.ai",
        "name": "Sahayak Verified Google User",
        "picture": "https://lh3.googleusercontent.com/avatar.jpg",
        "iss": "https://accounts.google.com",
        "aud": settings.GOOGLE_CLIENT_ID,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        payload = {
            "code": "eyValidMockGoogleIdToken.Payload.Signature",
            "redirectUri": "http://localhost:5173/auth/callback",
        }
        response = await client.post("/api/v1/auth/google", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "accessToken" in data or "access_token" in data
        token = data.get("accessToken") or data.get("access_token")
        assert token is not None

        # Verify access token works on /auth/me
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "googleuser@sahayak.ai"


@pytest.mark.asyncio
async def test_google_oauth_invalid_signature_rejected(client: AsyncClient):
    """Google ID token with invalid signature returns 401 Unauthorized."""
    from unittest.mock import patch

    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Invalid signature")):
        payload = {
            "code": "eyInvalidSigToken.Payload.BadSignature",
            "redirectUri": "http://localhost:5173/auth/callback",
        }
        response = await client.post("/api/v1/auth/google", json=payload)
        assert response.status_code == 401
        assert "Invalid Google token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_oauth_bad_audience_rejected(client: AsyncClient):
    """Google ID token issued for a different client ID returns 401."""
    from unittest.mock import patch

    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Token has wrong audience")):
        payload = {
            "code": "eyBadAudienceToken.Payload.Signature",
            "redirectUri": "http://localhost:5173/auth/callback",
        }
        response = await client.post("/api/v1/auth/google", json=payload)
        assert response.status_code == 401
        assert "Invalid Google token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_oauth_wrong_issuer_rejected(client: AsyncClient):
    """Google ID token issued by untrusted issuer returns 401."""
    from unittest.mock import patch

    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Wrong issuer")):
        payload = {
            "code": "eyWrongIssuerToken.Payload.Signature",
            "redirectUri": "http://localhost:5173/auth/callback",
        }
        response = await client.post("/api/v1/auth/google", json=payload)
        assert response.status_code == 401
        assert "Invalid Google token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_oauth_expired_token_rejected(client: AsyncClient):
    """Expired Google ID token returns 401."""
    from unittest.mock import patch

    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Token expired")):
        payload = {
            "code": "eyExpiredToken.Payload.Signature",
            "redirectUri": "http://localhost:5173/auth/callback",
        }
        response = await client.post("/api/v1/auth/google", json=payload)
        assert response.status_code == 401
        assert "Invalid Google token" in response.json()["detail"]

