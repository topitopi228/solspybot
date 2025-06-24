from fastapi import HTTPException
from sqlalchemy import select
from api.api_init_helper import api_helper
from core.models.user import User
from core.models.bot_wallet import BotWallet
from core.service.wallet_token_service import WalletTokenService
from api.api_init_helper import api_helper
import logging

logger = logging.getLogger(__name__)

from core.service.tracked_wallet_service import TrackedWalletService


class BotWalletService:
    def __init__(self, session_factory):

        self.wallet_token_service = WalletTokenService(session_factory=session_factory)
        self.tracked_wallet_service = TrackedWalletService(session_factory=session_factory, api_heler=api_helper)
        self.session_factory = session_factory

    async def add_wallet_to_bot(self, wallet_data, user: User) -> BotWallet | None:

        try:
            async with self.session_factory() as session:
                all_wallets = await session.execute(select(BotWallet).filter(BotWallet.user_id == user.id))
                all_wallets = all_wallets.scalars().all()
                for wallet in all_wallets:
                    if wallet.status:
                        wallet.status = False
                        session.add(wallet)

                # Проверяем, существует ли кошелек с таким адресом
                result = await session.execute(
                    select(BotWallet).filter(BotWallet.token_address == wallet_data.token_address))
                existing_wallet = result.scalar_one_or_none()
                if existing_wallet:
                    raise HTTPException(status_code=400, detail=f"Кошелек {wallet_data.token_address} уже существует")

                # Создаем новую сущность BotWallet
                new_wallet = BotWallet(
                    token_address=wallet_data.token_address,
                    private_key=wallet_data.private_key,
                    user_id=user.id,
                    status=True,
                )
                session.add(new_wallet)
                await session.commit()
                await session.refresh(new_wallet)
                logger.info(
                    f"Добавлен новый кошелек: {wallet_data.token_address} для пользователя {new_wallet.user_id}")
                return new_wallet

        except Exception as e:
            logger.error(f"Ошибка при добавлении кошелька {wallet_data.token_address}: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера при добавлении кошелька: {str(e)}")

    async def get_users_wallets(self, user: User) -> list[BotWallet] | None:

        try:
            async with self.session_factory() as session:
                result = await session.execute(select(BotWallet).filter(BotWallet.user_id == user.id))
                wallets = result.scalars().all()
                for wallet in wallets:
                    balance = await api_helper.solana_api.get_balance(wallet.token_address)
                    wallet.balance = balance
                    session.add(wallet)

                session.commit()

                return wallets
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)
