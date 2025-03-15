from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.bitquery_api import BitqueryAPI
from api.solana_api import SolanaAPI
from core.service.tracked_wallet_service import WalletService
from core.models.tracked_wallet import FollowMode, WalletStatus
import logging
tracked_wallet_router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletRequest(BaseModel):
    wallet_address: str
    follow_mode: FollowMode

def get_wallet_service() -> WalletService:
    """
    Фабрика для создания экземпляра WalletService с встроенным SolanaAPI.
    """
    return WalletService()

@tracked_wallet_router.post("/tracked_wallets/")
async def add_wallet(
    wallet_request: WalletRequest,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """
    Добавляет новый кошелёк в базу данных для отслеживания.
    """
    logger.info(f"Получен запрос на добавление кошелька: {wallet_request.wallet_address}")
    try:

        await wallet_service.add_wallet_data(wallet_address=wallet_request.wallet_address, follow_mode=wallet_request.follow_mode)
        logger.info(f"Кошелёк {wallet_request.wallet_address} успешно добавлен.")
        return {
            "message": f"Кошелёк {wallet_request.wallet_address} успешно добавлен для отслеживания.",
            "wallet_address": wallet_request.wallet_address,
            "follow_mode": wallet_request.follow_mode.value,
            "status": "active"
        }
    except ValueError as e:
        logger.error(f"Ошибка при добавлении кошелька {wallet_request.wallet_address}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@tracked_wallet_router.put("/tracked_wallets/")
async def update_wallet(
    wallet_address: str,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """
    Обновляет данные кошелька или статус кошелька в зависимости от параметров.
    """
    logger.info(f"Получен запрос на обновление кошелька: {wallet_address}")
    try:
        await wallet_service.update_wallet_data(wallet_address=wallet_address)
        logger.info(f"Данные кошелька {wallet_address} успешно обновлены.")
        return {"message": f"Данные кошелька {wallet_address} успешно обновлены."}
    except ValueError as e:
        logger.error(f"Ошибка при обновлении данных кошелька {wallet_address}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
