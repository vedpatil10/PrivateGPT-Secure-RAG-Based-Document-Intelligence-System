"""
Analytics API routes — usage metrics and dashboards.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db_session
from models.schemas import UsageStats
from core.dependencies import get_current_user, require_role
from services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    days: int = 30,
    current_user: dict = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db_session),
):
    """Get usage analytics for the organization."""
    stats = await AnalyticsService.get_usage_stats(
        org_id=current_user["org_id"],
        db=db,
        days=days,
    )
    return stats
