import logging
import httpx
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.models import User
from app.database.session import get_db

logger = logging.getLogger(__name__)

optional_bearer = HTTPBearer(auto_error=False)


class GoogleAuthError(Exception):
    """Raised when Google OAuth token verification or exchange fails."""
    def __init__(self, detail: str, status_code: int = 401):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_google_token(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Verify Google OAuth token or exchange authorization code.

        Validates token audience, issuer, expiry, and signature using Google's verification libraries.
        Does not trust unverified user identity parameters.
        Raises GoogleAuthError on any validation failure.
        """
        if not settings.GOOGLE_CLIENT_ID:
            logger.warning("GOOGLE_CLIENT_ID is not configured in settings")
            raise GoogleAuthError("Invalid Google token: GOOGLE_CLIENT_ID not configured on server")

        # 1. Check if the provided code is already an ID token (JWT format: 3 segments separated by dots starting with ey)
        if isinstance(code, str) and code.count(".") == 2 and code.startswith("ey"):
            try:
                id_info = id_token.verify_oauth2_token(
                    code,
                    google_requests.Request(),
                    audience=settings.GOOGLE_CLIENT_ID,
                )

                # Check issuer
                iss = id_info.get("iss")
                if iss not in ("accounts.google.com", "https://accounts.google.com"):
                    logger.warning(f"Google ID token invalid issuer: {iss}")
                    raise GoogleAuthError(f"Invalid Google token: invalid issuer '{iss}'")

                # Check audience
                aud = id_info.get("aud")
                if aud != settings.GOOGLE_CLIENT_ID:
                    logger.warning(f"Google ID token audience mismatch: {aud} != {settings.GOOGLE_CLIENT_ID}")
                    raise GoogleAuthError("Invalid Google token: audience mismatch")

                # Check expiration
                exp = id_info.get("exp")
                if exp and datetime.now(timezone.utc).timestamp() > exp:
                    logger.warning("Google ID token has expired")
                    raise GoogleAuthError("Invalid Google token: token has expired")

                logger.info("Successfully verified Google ID token directly")
                return {
                    "google_id": id_info["sub"],
                    "email": id_info["email"],
                    "name": id_info.get("name", id_info.get("email", "").split("@")[0]),
                    "picture": id_info.get("picture"),
                    "access_token": code,
                    "refresh_token": None,
                }
            except GoogleAuthError:
                raise
            except Exception as e:
                logger.warning(f"Direct ID token verification failed: {e}")
                err_msg = str(e).lower()
                if "expired" in err_msg:
                    raise GoogleAuthError("Invalid Google token: token has expired")
                elif "audience" in err_msg or "aud" in err_msg:
                    raise GoogleAuthError("Invalid Google token: audience mismatch")
                elif "issuer" in err_msg or "iss" in err_msg:
                    raise GoogleAuthError(f"Invalid Google token: invalid issuer ({e})")
                elif "signature" in err_msg or "algorithm" in err_msg:
                    raise GoogleAuthError(f"Invalid Google token: signature verification failed ({e})")
                else:
                    raise GoogleAuthError(f"Invalid Google token: {e}")

        # 2. Exchange authorization code with Google's OAuth2 token endpoint
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if settings.GOOGLE_CLIENT_SECRET:
            data["client_secret"] = settings.GOOGLE_CLIENT_SECRET

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_url, data=data)
                if response.status_code != 200:
                    logger.warning(f"Google token exchange returned status {response.status_code}")
                    raise GoogleAuthError(f"Invalid Google token: authorization code exchange failed with status {response.status_code}")
                tokens = response.json()

                # If an ID token was returned, verify it cryptographically
                if "id_token" in tokens:
                    try:
                        id_info = id_token.verify_oauth2_token(
                            tokens["id_token"],
                            google_requests.Request(),
                            audience=settings.GOOGLE_CLIENT_ID,
                        )

                        iss = id_info.get("iss")
                        if iss not in ("accounts.google.com", "https://accounts.google.com"):
                            raise GoogleAuthError(f"Invalid Google token: invalid issuer '{iss}'")

                        aud = id_info.get("aud")
                        if aud != settings.GOOGLE_CLIENT_ID:
                            raise GoogleAuthError("Invalid Google token: audience mismatch")

                        exp = id_info.get("exp")
                        if exp and datetime.now(timezone.utc).timestamp() > exp:
                            raise GoogleAuthError("Invalid Google token: token has expired")

                        return {
                            "google_id": id_info["sub"],
                            "email": id_info["email"],
                            "name": id_info.get("name", id_info.get("email", "").split("@")[0]),
                            "picture": id_info.get("picture"),
                            "access_token": tokens.get("access_token"),
                            "refresh_token": tokens.get("refresh_token"),
                        }
                    except GoogleAuthError:
                        raise
                    except Exception as e:
                        logger.error(f"Failed to verify received id_token: {e}")
                        raise GoogleAuthError(f"Invalid Google token: {e}")

                # Fallback to userinfo endpoint if id_token was absent
                if "access_token" in tokens:
                    userinfo_resp = await client.get(
                        "https://www.googleapis.com/oauth2/v2/userinfo",
                        headers={"Authorization": f"Bearer {tokens['access_token']}"},
                    )
                    if userinfo_resp.status_code == 200:
                        userinfo = userinfo_resp.json()
                        return {
                            "google_id": userinfo["id"],
                            "email": userinfo["email"],
                            "name": userinfo.get("name", ""),
                            "picture": userinfo.get("picture"),
                            "access_token": tokens["access_token"],
                            "refresh_token": tokens.get("refresh_token"),
                        }

                raise GoogleAuthError("Invalid Google token: neither id_token nor userinfo returned")
        except GoogleAuthError:
            raise
        except Exception as e:
            logger.error(f"Error communicating with Google OAuth servers: {e}")
            raise GoogleAuthError(f"Invalid Google token: error communicating with Google servers ({e})")

    async def get_or_create_user(self, google_data: Dict[str, Any]) -> User:
        result = await self.db.execute(select(User).where(User.email == google_data["email"]))
        user = result.scalar_one_or_none()

        if user:
            user.name = google_data["name"]
            user.picture = google_data.get("picture")
            user.updated_at = datetime.now(timezone.utc)
        else:
            user = User(
                email=google_data["email"],
                name=google_data["name"],
                picture=google_data.get("picture"),
                preferred_language="en-IN",
            )
            self.db.add(user)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    def create_access_token(self, user: User) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        payload = {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user if Bearer token is provided, otherwise None."""
    if not credentials or not credentials.credentials:
        return None
    auth_service = AuthService(db)
    payload = auth_service.verify_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        return None
    return await auth_service.get_user_by_id(payload["sub"])
