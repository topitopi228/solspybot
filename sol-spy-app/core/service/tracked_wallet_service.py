import logging

from solders.rpc.responses import RpcConfirmedTransactionStatusWithSignature
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from core.models.tracked_wallet import TrackedWallet  # Импорт модели TrackedWallet
from api.solana_api import SolanaAPI  # Импорт класса SolanaAPI
from core.models.tracked_wallet import FollowMode, WalletStatus
from core.db_helper import db_helper
from core.models.wallet_transaction import WalletTransaction, TransactionStatus
from core.models.wallet_transaction import TransactionAction


logger = logging.getLogger(__name__)


class WalletService:
    def __init__(self):
        self.solana_api = SolanaAPI()

    async def add_wallet_data(self, wallet_address: str, follow_mode: FollowMode):
        """
        Добавляет кошелёк в базу данных для отслеживания.
        """
        # Проверяем, существует ли уже кошелёк в базе
        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            existing_wallet = result.scalar_one_or_none()

        if existing_wallet:
            raise ValueError(f"Кошелёк {wallet_address} уже отслеживается.")

        # Получаем начальные данные о кошельке через Solana API
        try:
            balance = await self.solana_api.get_balance(wallet_address)
        except Exception as e:
            raise ValueError(f"Ошибка получения данных о балансе кошелька: {e}")

        # Создаём новую сущность TrackedWallet
        new_wallet = TrackedWallet(
            wallet_address=wallet_address,
            status=WalletStatus.ACTIVE,  # Устанавливаем статус "ACTIVE" по умолчанию
            follow_mode=follow_mode,  # Режим отслеживания передаётся как аргумент
            created_at=func.now(),
            last_activity_at=None,  # Пока нет активности
            sol_balance=balance  # Устанавливаем начальный баланс
        )
        async with db_helper.session_factory() as session:
        # Добавляем кошелёк в сессию
            try:
                session.add(new_wallet)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError(f"Ошибка: Кошелёк {wallet_address} уже существует в базе.")

    async def update_wallet_data(self, wallet_address: str):
        """
        Обновляет данные кошелька в базе данных.
        """
        # Получаем данные о кошельке из Solana API
        balance = await self.solana_api.get_balance(wallet_address)
        transactions = await self.solana_api.get_wallet_transactions(wallet_address, limit=5)

        # Получаем кошелек из базы данных
        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            tracked_wallet = result.scalar_one_or_none()

            if tracked_wallet.status != WalletStatus.ACTIVE:
                print(f"Кошелёк {wallet_address} имеет статус {tracked_wallet.status}. Обновление данных пропущено.")
                return
            if tracked_wallet:
                # Обновляем данные в сущности
                tracked_wallet.sol_balance = balance
                tracked_wallet.last_activity_at = func.now()  # Обновляем дату последней активности

                if transactions:
                    for transaction in transactions:
                        # Проверяем, что transaction — это RpcConfirmedTransactionStatusWithSignature
                        if not isinstance(transaction, RpcConfirmedTransactionStatusWithSignature):
                            logger.error(
                                f"Некорректный тип транзакции для кошелька {wallet_address}: {type(transaction)}")
                            continue

                        try:
                            # Доступ к signature через атрибут .signature
                            transaction_details = await self.solana_api.get_transaction_details(
                                transaction.signature  # Используем .signature вместо ['signature']
                            )
                            # Проверяем, существует ли уже транзакция в базе данных
                            result = await session.execute(
                                select(WalletTransaction).filter(
                                    WalletTransaction.transaction_hash == transaction_details.transaction_hash)
                            )
                            transaction_exists = result.scalar_one_or_none()  # Используем scalar_one_or_none для безопасной проверки

                            if not transaction_exists:
                                # Если транзакция не существует, добавляем ее в базу данных
                                new_transaction = WalletTransaction(
                                    wallet_id=tracked_wallet.id,
                                    transaction_hash=transaction_details.transaction_hash,
                                    transaction_action=transaction_details.transaction_action,
                                    status=TransactionStatus.SUCCESS,
                                    token_address=transaction_details.token_address,
                                    token_symbol=transaction_details.token_symbol,
                                    base_amount=transaction_details.base_amount,
                                    quote_amount=transaction_details.quote_amount,
                                    price=transaction_details.price,
                                    timestamp=func.now()  # Используем func.now() для консистентности
                                )
                                session.add(new_transaction)
                                logger.info(f"Добавлена новая транзакция: {transaction_details.transaction_hash}")
                        except Exception as e:
                            logger.error(f"Ошибка при обработке транзакции для кошелька {wallet_address}: {e}")

                    # Сохраняем все изменения в одной транзакции
                try:
                    await session.commit()
                    logger.info(f"Данные для кошелька {wallet_address} обновлены, транзакции обработаны.")
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Ошибка при сохранении данных для {wallet_address}: {e}")
                    raise ValueError(f"Не удалось обновить данные кошелька: {str(e)}")

    async def update_wallet_status(self, wallet_address: str, new_status: WalletStatus):
        """
        Обновляет статус кошелька.
        """
        # Проверяем, существует ли кошелёк в базе данных
        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            tracked_wallet = result.scalar_one_or_none()

            if not tracked_wallet:
                raise ValueError(f"Кошелёк {wallet_address} не найден в базе данных.")

            # Обновляем статус
            tracked_wallet.status = new_status

            # Сохраняем изменения в базе данных
            await session.commit()
        print(f"Статус кошелька {wallet_address} успешно обновлён на {new_status.name}.")

    async def close(self):
        """
        Закрывает соединение с клиентом.
        """
        await self.solana_api.close()
