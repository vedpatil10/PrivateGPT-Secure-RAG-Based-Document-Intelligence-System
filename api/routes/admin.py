"""
Admin API routes — user management, audit logs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models.database import get_db_session
from models.schemas import UpdateUserRoleRequest, UpdateUserStatusRequest
from models.audit import AuditLog
from models.user import Role, User
from core.dependencies import require_role

router = APIRouter()


@router.get("/users")
async def list_users(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db_session),
):
    """List all users in the organization."""
    result = await db.execute(
        select(User).where(User.org_id == current_user["org_id"])
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "last_login": str(u.last_login) if u.last_login else None,
        }
        for u in users
    ]


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    action: str | None = None,
    user_email: str | None = None,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db_session),
):
    """View audit logs for the organization."""
    query = (
        select(AuditLog)
        .where(AuditLog.org_id == current_user["org_id"])
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        query = query.where(AuditLog.action == action)
    if user_email:
        query = query.where(AuditLog.user_email == user_email)

    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "user_email": l.user_email,
            "action": l.action,
            "query_text": l.query_text,
            "created_at": str(l.created_at),
            "duration_ms": l.duration_ms,
        }
        for l in logs
    ]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a user's role within the current organization."""
    try:
        new_role = Role(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.org_id == current_user["org_id"],
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(role=new_role)
    )
    await db.commit()

    return {"status": "updated", "user_id": user_id, "role": new_role.value}


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: UpdateUserStatusRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db_session),
):
    """Activate or deactivate a user within the current organization."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.org_id == current_user["org_id"],
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=request.is_active)
    )
    await db.commit()

    return {"status": "updated", "user_id": user_id, "is_active": request.is_active}
