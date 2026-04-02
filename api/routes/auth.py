"""
Authentication API routes — register, login, token refresh, invite.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db_session
from models.schemas import (
    InviteRequest,
    LoginRequest,
    RefreshTokenResponse,
    RegisterRequest,
    TokenResponse,
)
from services.auth_service import AuthService
from core.dependencies import get_current_user, require_role

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new organization with an admin user."""
    try:
        result = await AuthService.register(
            org_name=request.org_name,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Authenticate and receive a JWT token."""
    try:
        result = await AuthService.login(
            email=request.email,
            password=request.password,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Refresh the current access token."""
    try:
        return await AuthService.refresh_token(
            user_id=current_user["user_id"],
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/invite", response_model=dict)
async def invite_user(
    request: InviteRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db_session),
):
    """Invite a user to the current organization (admin only)."""
    try:
        result = await AuthService.invite_user(
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            org_id=current_user["org_id"],
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
):
    """Get current authenticated user info."""
    return current_user
