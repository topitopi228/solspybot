from asyncio.log import logger

from sqlalchemy import select
from typing import Optional

from core.models.tracked_wallet import TrackedWallet
from core.models.wallet_token import WalletToken
from api.helius_api import HeliusApi
from core.db_helper import db_helper





class WalletTokenService:
    def __init__(self,session_factory):
        self.helius_api = HeliusApi()
        self.session_factory = session_factory


    async def update_wallet_token_balance(self, wallet_address: str, token_address: str) -> Optional[WalletToken]:
        try:
            # 1. Создаём сессию через db_helper
            async with self.session_factory() as session:
                # 2. Проверяем, существует ли кошелёк в таблице tracked_wallets
                result = await session.execute(
                    select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address)
                )
                existing_wallet = result.scalar_one_or_none()

                if not existing_wallet:
                    logger.error(f"Кошелёк с адресом {wallet_address} не найден в tracked_wallets")
                    return None

                wallet_id = existing_wallet.id

                # 3. Получаем данные о балансе токена через Helius API
                token_data = await self.helius_api.get_token_balance(wallet_address, token_address)
                logger.info(f"Получены данные о токене {token_address} для кошелька {wallet_address}: {token_data}")

                if not token_data:
                    logger.error(f"Не удалось получить данные о токене {token_address} для кошелька {wallet_address}")
                    return None

                # 4. Извлекаем необходимые поля
                balance = token_data.get("balance", 0.0)
                token_symbol = token_data.get("symbol", None)

                # 5. Ищем существующую запись в базе данных
                wallet_token = await session.execute(
                    select(WalletToken).filter(
                        WalletToken.wallet_id == wallet_id,
                        WalletToken.token_address == token_address
                    )
                )
                wallet_token = wallet_token.scalar_one_or_none()

                if wallet_token:
                    # 6. Если запись существует, обновляем её
                    wallet_token.balance = balance
                    wallet_token.token_symbol = token_symbol if token_symbol else wallet_token.token_symbol
                    logger.info(
                        f"Обновлена запись в wallet_tokens: wallet_id={wallet_id}, token_address={token_address}, balance={balance}")
                else:
                    # 7. Если записи нет, создаём новую
                    wallet_token = WalletToken(
                        wallet_id=wallet_id,
                        token_address=token_address,
                        token_symbol=token_symbol,
                        balance=balance
                    )
                    session.add(wallet_token)
                    logger.info(
                        f"Создана новая запись в wallet_tokens: wallet_id={wallet_id}, token_address={token_address}, balance={balance}")

                # 8. Коммитим изменения
                await session.commit()
                await session.refresh(wallet_token)
                return wallet_token

        except Exception as e:
            logger.error(
                f"Ошибка при обновлении баланса токена {token_address} для кошелька {wallet_address}: {str(e)}")
            # Откатываем изменения в случае ошибки
            async with db_helper.session_factory() as session:
                await session.rollback()
            return None