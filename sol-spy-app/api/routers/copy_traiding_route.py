import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
import logging

from fastapi.security import APIKeyHeader
from pydantic import BaseModel, field_validator

from api.api_init_helper import api_helper
from api.routers.auth_utils import TokenUtils
from core.db_helper import db_helper
from core.models.user import User
from core.service.copy_traiding_service import CopyTradingService

router = APIRouter(prefix="/copy_trading", tags=["copy_trading"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WalletTrackingRequest(BaseModel):
    wallet_address: str
    interval_seconds: Optional[int] = 10

    class Config:
        from_attributes = True



# Функція для отримання TokenUtils як залежності
async def get_token_utils():
    return TokenUtils(db_helper.session_factory)

# Верифікація токена
async def verify_token(
    access_token_code: str = Depends(APIKeyHeader(name="Authorization", auto_error=True)),
    token_utils: TokenUtils = Depends(get_token_utils)
):
    return await token_utils.verify_token(access_token_code)

def get_copy_trading_service(user: User = Depends(verify_token)) -> CopyTradingService:
    return CopyTradingService(db_helper.session_factory, api_helper=api_helper, user=user)





@router.post("/start-tracking/")
async def start_tracking_without_actions(
        wallet_request: WalletTrackingRequest,
        user: User = Depends(verify_token),
        copy_trading_service: CopyTradingService = Depends(get_copy_trading_service)
):
    logger.info(f"Получен запрос на запуск пассивного отслеживания для {wallet_request.wallet_address}")
    try:
        await copy_trading_service.start_tracking_without_any_actions(wallet_request.wallet_address, user,
                                                                      wallet_request.interval_seconds)
        return {
            "message": f"Пассивное отслеживание для {wallet_request.wallet_address} запущено с интервалом {wallet_request.interval_seconds} секунд",
            "wallet_address": wallet_request.wallet_address,
            "interval_seconds": wallet_request.interval_seconds
        }
    except Exception as e:
        logger.error(f"Ошибка при запуске пассивного отслеживания для {wallet_request.wallet_address}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при запуске пассивного отслеживания: {str(e)}")


@router.post("/start-tracking-and-copy-trading/")
async def start_tracking(
        wallet_request: WalletTrackingRequest,
        user: User = Depends(verify_token),
        copy_trading_service: CopyTradingService = Depends(get_copy_trading_service)
):
    logger.info(f"Получен запрос на запуск пассивного отслеживания для {wallet_request.wallet_address}")
    try:

        await copy_trading_service.start_tracking_without_any_actions(wallet_request.wallet_address, user,10)
        return {
            "message": f"Пассивное отслеживание для {wallet_request.wallet_address} запущено с интервалом {wallet_request.interval_seconds} секунд",
            "wallet_address": wallet_request.wallet_address,
            "interval_seconds": wallet_request.interval_seconds
        }
    except Exception as e:
        logger.error(f"Ошибка при запуске пассивного отслеживания для {wallet_request.wallet_address}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при запуске пассивного отслеживания: {str(e)}")


@router.get("/tracking-status/{wallet_address}")
async def get_tracking_status(
        wallet_address: str,
        copy_trading_service: CopyTradingService = Depends(get_copy_trading_service)
):
    logger.info(f"Получен запрос на проверку статуса кошелька: {wallet_address}")
    try:
        is_tracking = wallet_address in copy_trading_service.tracking_tasks
        return {
            "wallet_address": wallet_address,
            "is_tracking": is_tracking,
            "message": f"Кошелёк {wallet_address} {'отслеживается' if is_tracking else 'не отслеживается'}"
        }
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса кошелька {wallet_address}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке статуса: {str(e)}")
