from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.core.config import settings
from app.schemas.schemas import GoogleAuthRequest, TokenResponse, UserResponse, ErrorResponse
from app.services.auth import AuthService, get_auth_service, GoogleAuthError


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/google")


@router.post(
    "/auth/google",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def google_auth(
    request: GoogleAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    if not settings.ENABLE_OAUTH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OAuth not enabled",
        )

    try:
        google_data = await auth_service.verify_google_token(request.code, request.redirect_uri)
        if not google_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            )
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
        )

    user = await auth_service.get_or_create_user(google_data)
    access_token = auth_service.create_access_token(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/auth/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse},
    },
)
async def get_current_user(
    authorization: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        payload = jwt.decode(authorization, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserResponse.model_validate(user)