from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from starlette.responses import JSONResponse

from api.routers.auth_utils import TokenUtils

from core.db_helper import db_helper
from core.models.user import User
from core.models.wallet_transaction import TransactionAction, TransactionStatus
from core.service.tracked_wallet_service import TrackedWalletService
from core.models.tracked_wallet import FollowMode, CopyMode
from api.api_init_helper import api_helper
import logging

router = APIRouter(prefix="/tracked-wallet", tags=["tracked-wallets"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackedWalletRequest(BaseModel):
    wallet_address: str

    class Config:
        from_attributes = True


class ChangeTrackedWalletModeRequest(BaseModel):
    wallet_address: str
    follow_mode: str

    class Config:
        from_attributes = True


class TrackedWalletResponse(BaseModel):
    id: int
    bot_wallet_id: int
    wallet_address: str
    follow_mode: FollowMode | None = None
    copy_mode: CopyMode | None = None
    is_tracking: bool
    created_at: datetime
    last_activity_at: datetime | None = None
    sol_balance: float | None = None

    class Config:
        from_attributes = True


class TrackedWalletTransactionResponse(BaseModel):
    id: int
    wallet_id: int
    transaction_action: TransactionAction | None = None
    transaction_hash: str | None = None
    status: TransactionStatus | None = None
    token_address: str | None = None
    token_symbol: str | None = None
    buy_amount: float | None = None
    sell_amount: float | None = None
    transfer_amount: float | None = None
    dex_name: str | None = None
    price: float | None = None
    timestamp: datetime | None = None

    class Config:
        from_attributes = True


def get_tracked_wallet_service() -> TrackedWalletService:
    return TrackedWalletService(db_helper.session_factory, api_heler=api_helper)


async def get_token_utils():
    return TokenUtils(db_helper.session_factory)


async def verify_token(
        access_token_code: str = Depends(APIKeyHeader(name="Authorization", auto_error=True)),
        token_utils: TokenUtils = Depends(get_token_utils)
):
    return await token_utils.verify_token(access_token_code)


@router.post("/")
async def add_wallet(
        tracked_wallet_request: TrackedWalletRequest,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),
):
    if not user:
        raise HTTPException(status_code=401)

    try:

        await tracked_wallet_service.add_wallet_data(tracked_wallet_request.wallet_address, user)
        return {"message": "Wallet completed successfully", "wallet_address": tracked_wallet_request.wallet_address}
    except ValueError as e:
        logger.error(f"Ошибка при добавлении кошелька {tracked_wallet_request.wallet_address}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bot_tracking_wallets", response_model=list[TrackedWalletResponse])
async def bot_tracking_wallets(
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),
):
    if not user:
        raise HTTPException(status_code=401)
    try:
        tracked_wallets = await tracked_wallet_service.get_user_tracking_wallets(user)
        print(tracked_wallets)
        return tracked_wallets
    except ValueError as e:

        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении данных отслежуемих кошельков")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")


@router.put("/status")
async def update_wallet(
        wallet_status_request: ChangeTrackedWalletModeRequest,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),
):
    if not user:
        raise HTTPException(status_code=401)

    try:
        follow_mode = FollowMode(wallet_status_request.follow_mode)
        await tracked_wallet_service.update_wallet_status(wallet_status_request.wallet_address, follow_mode)
        logger.info(f"Данные кошелька {wallet_status_request.wallet_address} успешно обновлены.")
        return JSONResponse(status_code=201, content={"detail": "Данные кошелька успешно обновлены"})
    except ValueError as e:
        logger.error(f"Ошибка при обновлении данных кошелька {wallet_status_request.wallet_address}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{wallet_address}", response_model=TrackedWalletResponse)
async def get_wallet_by_address(
        wallet_address: str,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),
):
    if not user:
        raise HTTPException(status_code=401)
    try:
        tracked_wallet = await tracked_wallet_service.get_wallet_by_address(wallet_address)
        return tracked_wallet
    except ValueError as e:
        logger.warning(f"Кошелёк {wallet_address} не найден: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/stop-tracking/{wallet_address}")
async def stop_track_wallet(
        wallet_address: str,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),

):
    if not user:
        raise HTTPException(status_code=401)
    try:
        await tracked_wallet_service.stop_tracking(wallet_address, user)

    except ValueError as e:
        logger.warning(f"неудалось перестать отслеживать")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/start-tracking/{wallet_address}")
async def stop_track_wallet(
        wallet_address: str,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),

):
    if not user:
        raise HTTPException(status_code=401)
    try:
        await tracked_wallet_service.start_tracking(wallet_address, user)
    except ValueError as e:
        logger.warning(f"неудалось начать отслеживать")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete/{wallet_address}")
async def delete_tracked_wallet(
        wallet_address: str,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),
):
    if not user:
        raise HTTPException(status_code=401)
    try:
        await tracked_wallet_service.delete_wallet(wallet_address, user)
    except ValueError as e:
        logger.warning(f"неудалось начать отслеживать")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transaction/{wallet_address}", response_model=list[TrackedWalletTransactionResponse])
async def get_wallet_transactions_by_address(
        wallet_address: str,
        tracked_wallet_service: TrackedWalletService = Depends(get_tracked_wallet_service),
        user: User = Depends(verify_token),
):
    if not user:
        raise HTTPException(status_code=401)
    try:
        wallet_transactions = await tracked_wallet_service.get_wallet_transactions(wallet_address)
        return wallet_transactions
    except ValueError as e:
        logger.warning(f"Кошелёк {wallet_address} не найден: {e}")
        raise HTTPException(status_code=400, detail=str(e))
