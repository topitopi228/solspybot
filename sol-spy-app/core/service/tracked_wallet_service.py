import logging
import sys

from typing import TYPE_CHECKING

from solders.rpc.responses import RpcConfirmedTransactionStatusWithSignature
from sqlalchemy import func, delete

from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from api.api_init_helper import ApiHelper
from core.models.bot_wallet import BotWallet
from core.models.tracked_wallet import TrackedWallet
from core.models.tracked_wallet import FollowMode
from core.models.wallet_transaction import WalletTransaction, TransactionStatus
from core.db_helper import db_helper
from core.models.user import User

if TYPE_CHECKING:
    from core.models.wallet_transaction import WalletTransaction

logger = logging.getLogger(__name__)

logger.debug(f"Python Path: {sys.path}")


class TrackedWalletService:
    def __init__(self, session_factory, api_heler: ApiHelper):
        self.api_helper = api_heler
        self.session_factory = session_factory

    async def add_wallet_data(self, wallet_address: str, user: User):

        # Проверяем, существует ли уже кошелёк в базе
        async with self.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            existing_wallet = result.scalar_one_or_none()

        if existing_wallet:
            raise ValueError(f"Кошелёк {wallet_address} уже отслеживается.")

        async with self.session_factory() as session:
            result = await session.execute(
                select(BotWallet).filter(BotWallet.user_id == user.id).filter(BotWallet.status == True))
            bot_wallet = result.scalar_one_or_none()

        # Получаем начальные данные о кошельке через Solana API
        try:
            balance = await self.api_helper.solana_api.get_balance(wallet_address)
            print(balance)
        except Exception as e:
            raise ValueError(f"Ошибка получения данных о балансе кошелька: {e}")

        # Создаём новую сущность TrackedWallet
        new_wallet = TrackedWallet(
            bot_wallet_id=bot_wallet.id,
            wallet_address=wallet_address,
            follow_mode=None,  # Режим отслеживания передаётся как аргумент
            copy_mode= None,
            is_tracking=False,
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

    async def get_user_tracking_wallets(self, user):
        async with self.session_factory() as session:
            result = await session.execute(
                select(BotWallet).filter(BotWallet.user_id == user.id).filter(BotWallet.status == True))
            bot_wallet = result.scalar_one_or_none()

        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.bot_wallet_id == bot_wallet.id)
            )
            tracked_wallets = result.scalars().all()

        return tracked_wallets

    async def update_wallet_data(self, wallet_address: str):

        # Получаем данные о кошельке из Solana API
        balance = await self.api_helper.solana_api.get_balance(wallet_address)
        transactions = await self.api_helper.solana_api.get_wallet_transactions(wallet_address, limit=5)
        print(transactions[0].signature)
        added_transactions = []

        # Получаем кошелек из базы данных
        async with self.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            tracked_wallet = result.scalar_one_or_none()
            print(tracked_wallet.id)

            if tracked_wallet.follow_mode != FollowMode.COPY and tracked_wallet.follow_mode != FollowMode.MONITOR:
                print(
                    f"Кошелёк {wallet_address} имеет статус {tracked_wallet.follow_mode}. Обновление данных пропущено.")
                return
            if tracked_wallet:
                # Обновляем данные в сущности
                tracked_wallet.sol_balance = balance
                tracked_wallet.last_activity_at = func.now()

                if transactions:
                    for transaction in transactions:
                        # Проверяем, что transaction — это RpcConfirmedTransactionStatusWithSignature
                        if not isinstance(transaction, RpcConfirmedTransactionStatusWithSignature):
                            logger.error(
                                f"Некорректный тип транзакции для кошелька {wallet_address}: {type(transaction)}")
                            continue

                        try:
                            # Проверяем, существует ли уже транзакция в базе данных
                            result = await session.execute(
                                select(WalletTransaction).filter(
                                    WalletTransaction.transaction_hash == str(transaction.signature))
                            )
                            existing_transaction = result.scalar_one_or_none()

                            # Если транзакция уже есть в БД, используем её данные
                            if existing_transaction:
                                logger.info(
                                    f"Транзакция {transaction.signature} уже существует в БД, пропускаем вызов Bitquery.")
                                continue  # Пропускаем вызов get_transaction_info
                            else:
                                transaction_details = await self.api_helper.helius_api.get_transaction_info(
                                    str(transaction.signature))

                                # Добавляем новую транзакцию в БД
                                new_transaction = WalletTransaction(
                                    wallet_id=tracked_wallet.id,
                                    transaction_hash=transaction_details["transaction_hash"],
                                    transaction_action=transaction_details["transaction_type"],
                                    status=TransactionStatus.SUCCESS,
                                    token_address=transaction_details["token_address"],
                                    token_symbol=transaction_details["token_symbol"],
                                    buy_amount=transaction_details["buy_amount"],
                                    sell_amount=transaction_details["sell_amount"],
                                    transfer_amount=transaction_details["transfer_amount"],
                                    dex_name=transaction_details["dex_name"],
                                    timestamp=func.now()
                                )
                                session.add(new_transaction)
                                logger.info(f"Добавлена новая транзакция: {transaction_details['transaction_hash']}")
                                # Добавляем транзакцию в список возвращаемых данных
                                added_transactions.append({
                                    "transaction_hash": transaction_details["transaction_hash"],
                                    "transaction_action": transaction_details["transaction_type"],
                                    "token_address": transaction_details["token_address"],
                                    "token_symbol": transaction_details["token_symbol"],
                                    "buy_amount": transaction_details["buy_amount"],
                                    "sell_amount": transaction_details["sell_amount"],
                                    "transfer_amount": transaction_details["transfer_amount"],
                                    "dex_name": transaction_details["dex_name"],
                                    "timestamp": func.now()
                                })

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

        return added_transactions

    async def get_wallet_by_address(self, wallet_address: str) -> TrackedWallet:

        async with self.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address)
            )
            tracked_wallet = result.scalar_one_or_none()
            if not tracked_wallet:
                logger.warning(f"Кошелёк {wallet_address} не найден в базе данных")
                raise ValueError(f"Кошелёк {wallet_address} не найден в базе данных")
            return tracked_wallet

    async def update_wallet_status(self, wallet_address: str, follow_mode: FollowMode):
        """
        Обновляет статус кошелька.
        """
        # Проверяем, существует ли кошелёк в базе данных
        async with self.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            tracked_wallet = result.scalar_one_or_none()

            if not tracked_wallet:
                raise ValueError(f"Кошелёк {wallet_address} не найден в базе данных.")

            # Обновляем статус
            tracked_wallet.follow_mode = follow_mode

            tracked_wallet.is_tracking = True

            # Сохраняем изменения в базе данных
            await session.commit()
        print(f"Статус кошелька {wallet_address} успешно обновлён на {follow_mode.name}.")

    async def get_wallet_transactions(self, wallet_address: str) -> list[WalletTransaction]:
        tracked_wallet = await self.get_wallet_by_address(wallet_address)
        async with self.session_factory() as session:
            result = await session.execute(
                select(WalletTransaction).filter(WalletTransaction.wallet_id == tracked_wallet.id)
            )
            wallet_transactions = result.scalars().all()

            if not wallet_transactions:
                raise ValueError(f"немає трензацій для цього адреса або нема адреса")
            return wallet_transactions

    async def stop_tracking(self, wallet_address: str, user: User) -> None:

        try:
            async with self.session_factory() as session:

                result = await session.execute(
                    select(TrackedWallet)
                    .filter(
                        TrackedWallet.wallet_address == wallet_address,
                        TrackedWallet.bot_wallet_id.in_(
                            select(BotWallet.id).filter(BotWallet.user_id == user.id)
                        )
                    )
                )
                tracked_wallet = result.scalars().first()

                if not tracked_wallet:
                    logger.error(f"Гаманець {wallet_address} для користувача {user.id} не знайдено")
                    raise ValueError(
                        "в юзера нема такого гаманця"
                    )

                # Оновлюємо поля
                tracked_wallet.is_tracking = False
                tracked_wallet.follow_mode = None

                # Комітимо зміни
                await session.commit()
                logger.info(f"Відстежування гаманця {wallet_address} зупинено: is_tracking=False, follow_mode=None")

        except Exception as e:
            logger.error(f"Помилка при зупиненні відстежування гаманця {wallet_address}: {e}")
            raise ValueError(
                "невдалось зупинити трекінг"
            )

    async def start_tracking(self, wallet_address: str, user: User) -> None:

        try:
            async with self.session_factory() as session:

                result = await session.execute(
                    select(TrackedWallet)
                    .filter(
                        TrackedWallet.wallet_address == wallet_address,
                        TrackedWallet.bot_wallet_id.in_(
                            select(BotWallet.id).filter(BotWallet.user_id == user.id)
                        )
                    )
                )
                tracked_wallet = result.scalars().first()

                if not tracked_wallet:
                    logger.error(f"Гаманець {wallet_address} для користувача {user.id} не знайдено")
                    raise ValueError(
                        "в юзера нема такого гаманця"
                    )

                # Оновлюємо поля
                tracked_wallet.is_tracking = True
                tracked_wallet.follow_mode = FollowMode.MONITOR

                # Комітимо зміни
                await session.commit()
                logger.info(f"Відстежування гаманця {wallet_address} зупинено: is_tracking=False, follow_mode=None")

        except Exception as e:
            logger.error(f"Помилка при зупиненні відстежування гаманця {wallet_address}: {e}")
            raise ValueError(
                "невдалось зупинити трекінг"
            )

    async def delete_wallet(self, wallet_address: str, user: User) -> None:
        try:
            async with self.session_factory() as session:
                # Знаходимо гаманець у таблиці tracked_wallets
                result = await session.execute(
                    select(TrackedWallet)
                    .filter(
                        TrackedWallet.wallet_address == wallet_address,
                        TrackedWallet.bot_wallet_id.in_(
                            select(BotWallet.id).filter(BotWallet.user_id == user.id)
                        )
                    )
                )
                tracked_wallet = result.scalars().first()

                if not tracked_wallet:
                    logger.error(f"Гаманець {wallet_address} для користувача {user.id} не знайдено")
                    raise ValueError(
                        f"Гаманець {wallet_address} не знайдено для цього користувача"
                    )

                # Видаляємо всі транзакції, пов’язані з гаманцем
                await session.execute(
                    delete(WalletTransaction).where(WalletTransaction.wallet_id == tracked_wallet.id)
                )

                # Видаляємо гаманець
                await session.delete(tracked_wallet)
                await session.commit()
                logger.info(f"Гаманець {wallet_address} успішно видалено для користувача {user.id}")

        except Exception as e:
            logger.error(f"Помилка при видаленні гаманця {wallet_address}: {e}")
            await session.rollback()
            raise ValueError(
                f"Не вдалося видалити гаманець {wallet_address}: {str(e)}"
            )

    async def close(self):
        """
        Закрывает соединение с клиентом.
        """
        await self.api_helper.solana_api.close()
