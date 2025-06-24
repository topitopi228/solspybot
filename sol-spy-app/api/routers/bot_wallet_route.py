import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, validator, field_validator
from pyexpat.errors import messages
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_helper import db_helper
from core.service.bot_wallet_service import BotWalletService  # Импортируй свой сервис
from core.models.my_wallet_transaction import TransactionAction
from core.models.user import User
from api.routers.auth_utils import TokenUtils
import logging

router = APIRouter(prefix="/bot_wallets", tags=["bot_wallet"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectedWalletToBotRequest(BaseModel):
    token_address: str
    private_key: str
    status: bool

class UserWalletsResponse(BaseModel):
    id: int
    user_id: int
    token_address: str
    private_key: str
    status: bool
    balance: float | None = None


def get_bot_service() -> BotWalletService:
    return BotWalletService(db_helper.session_factory)


async def get_token_utils():
    return TokenUtils(db_helper.session_factory)


async def verify_token(
    access_token_code: str = Depends(APIKeyHeader(name="Authorization", auto_error=True)),
    token_utils: TokenUtils = Depends(get_token_utils)
):
    return await token_utils.verify_token(access_token_code)


@router.post("/add-wallet-for-bot")
async def connet_wallet_to_bot(
        wallet_request: ConnectedWalletToBotRequest,
        bot_service: BotWalletService = Depends(get_bot_service),
        user: User = Depends(verify_token)
):
    if not user:
        raise HTTPException(status_code=401)

    try:
          await bot_service.add_wallet_to_bot(wallet_request, user)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/user_wallets",response_model=list[UserWalletsResponse])
async def get_user_wallets(
        bot_service: BotWalletService = Depends(get_bot_service),
        user: User = Depends(verify_token)
):
    if not user:
        raise HTTPException(status_code=401)

    try:
        bot_wallets=await bot_service.get_users_wallets(user)
        return bot_wallets
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))



