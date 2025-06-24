import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from api.routers.auth_utils import TokenUtils
from core.db_helper import db_helper
from core.models.user import User
from core.service.tracked_statistics_service import TrackedStatisticsService

router = APIRouter(prefix="/tracked-statistics", tags=["tracked-statistics"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackedStatisticsRequest(BaseModel):
    wallet_address: str

    class Config:
        from_attributes = True


class TrackedStatisticsResponse(BaseModel):
    id: int
    tracked_wallet_id: int
    deal_count: int | None = None
    earned_sol: float | None = None
    average_weakly_deals: float | None = None
    net_sol_increase: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


def get_tracked_statistics_service() -> TrackedStatisticsService:
    return TrackedStatisticsService(db_helper.session_factory)


async def get_token_utils():
    return TokenUtils(db_helper.session_factory)


async def verify_token(
        access_token_code: str = Depends(APIKeyHeader(name="Authorization", auto_error=True)),
        token_utils: TokenUtils = Depends(get_token_utils)
):
    return await token_utils.verify_token(access_token_code)


@router.get("/all/{wallet_address}", response_model=List[TrackedStatisticsResponse])
async def get_tracked_wallet_statistics(
        wallet_address: str,
        tracked_statistics_service: TrackedStatisticsService = Depends(get_tracked_statistics_service),
        user: User = Depends(verify_token)
):
    if not user:
        raise HTTPException(status_code=401)
    try:

        return await tracked_statistics_service.get_statistics_for_bot_wallet(user,wallet_address)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении  статистики отслежуемих кошельков")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")
