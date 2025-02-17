from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.solana_api import SolanaAPI
from core.service.tracked_wallet_service import WalletService
from core.models.tracked_wallet import FollowMode, WalletStatus

tracked_wallet_router = APIRouter()


@tracked_wallet_router.post("/tracked_wallets/")
async def add_wallet(
        wallet_address: str,
        follow_mode: FollowMode,
):
    """
    Добавляет новый кошелёк в базу данных для отслеживания.
    """
    wallet_service = WalletService()

    try:
        await wallet_service.add_wallet_data(wallet_address=wallet_address, follow_mode=follow_mode)
        return {"message": f"Кошелёк {wallet_address} успешно добавлен для отслеживания."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@tracked_wallet_router.put("/tracked_wallets/")
async def update_wallet(
        wallet_address: str,
        new_status: Optional[WalletStatus] = None  # new_status может быть пустым
):
    """
    Обновляет данные кошелька или статус кошелька в зависимости от параметров.
    """
    wallet_service = WalletService()

    # Если передан новый статус, обновляем только статус кошелька
    if new_status:
        try:
            await wallet_service.update_wallet_status(wallet_address=wallet_address, new_status=new_status)
            return {"message": f"Статус кошелька {wallet_address} успешно обновлён на {new_status.name}."}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Если не передан новый статус, обновляем данные кошелька
    try:
        await wallet_service.update_wallet_data(wallet_address=wallet_address)
        return {"message": f"Данные кошелька {wallet_address} успешно обновлены."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
