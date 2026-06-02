from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import FacebookAuthError
from app.schemas.auth import (
    ChangePasswordRequest,
    FacebookOAuthURL,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.base import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register with email & password",
)
async def register(body: RegisterRequest, db: DBSession):
    """Create a new account. Returns JWT tokens immediately."""
    service = AuthService(db)
    return await service.register(body)


@router.post("/login", response_model=TokenResponse, summary="Login with email & password")
async def login(body: LoginRequest, db: DBSession):
    """Login and receive access + refresh tokens."""
    service = AuthService(db)
    return await service.login(body)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_tokens(body: RefreshTokenRequest, db: DBSession):
    """Exchange a valid refresh token for a new access token."""
    service = AuthService(db)
    return await service.refresh_tokens(body.refresh_token)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Change password for the currently authenticated user."""
    service = AuthService(db)
    await service.change_password(current_user, body)
    return MessageResponse(message="Password changed successfully")


@router.get(
    "/facebook/login",
    response_model=FacebookOAuthURL,
    summary="Get Facebook OAuth URL",
)
async def facebook_login():
    """Returns the Facebook OAuth URL. Open it in a browser to start the OAuth flow."""
    service = AuthService.__new__(AuthService)
    return service.get_oauth_url()


@router.get(
    "/facebook/callback",
    response_model=TokenResponse,
    summary="Facebook OAuth callback",
)
async def facebook_callback(
    code: str | None = Query(None, description="OAuth code returned by Facebook"),
    error: str | None = Query(None),
    error_code: str | None = Query(None),
    error_message: str | None = Query(None),
    state: str | None = Query(None),
    db: DBSession = None,
):
    """
    Facebook redirects here after the user authorises the app.
    Returns JWT tokens. You do **not** call this manually — Facebook calls it.
    """
    if error or error_message:
        raise HTTPException(
            status_code=400, 
            detail=f"Facebook OAuth Error: {error_message or error} (Code: {error_code})"
        )
        
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing from Facebook")

    try:
        service = AuthService(db)
        return await service.facebook_callback(code)
    except FacebookAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: CurrentUser):
    """Returns the profile of the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        profile_picture=current_user.profile_picture,
        is_active=current_user.is_active,
        has_password=current_user.hashed_password is not None,
        created_at=current_user.created_at,
    )
