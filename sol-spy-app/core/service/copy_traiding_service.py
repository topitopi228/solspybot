
from typing import Dict

from core.models.bot_wallet import BotWallet
from core.models.tracked_wallet import FollowMode, TrackedWallet
from core.models.my_wallet_transaction import TransactionAction, TransactionStatus, MyWalletTransaction
from core.service.wallet_token_service import WalletTokenService
import base58
import logging
import time

import asyncio

from fastapi import HTTPException

from solders.keypair import Keypair

from sqlalchemy import select, func

from solders.pubkey import Pubkey
from core.models.user import User

from urllib3.exceptions import DecodeError

logger = logging.getLogger(__name__)

from core.service.tracked_wallet_service import TrackedWalletService

from api.api_init_helper import ApiHelper


class CopyTradingService:

    def __init__(self, session_factory, api_helper: ApiHelper,user: User):
        self.tracked_wallet_service = TrackedWalletService(session_factory=session_factory, api_heler=api_helper)
        self.wallet_token_service = WalletTokenService(session_factory=session_factory)
        self.api_helper = api_helper
        self.session_factory = session_factory
        self.user: User = user
        self.token_balances = {}  # Для зберігання балансів токенів
        self.our_wallet_address = None  # Ініціалізація адреси гаманця


    async def _load_bot_wallet(self, user: User) -> Keypair:
        try:
            private_key = await  self.get_active_user_wallet(user)
            private_key_bytes = base58.b58decode(private_key.strip())
            if len(private_key_bytes) != 64:
                raise ValueError(f"Ожидается 64 байта")
            keypair = Keypair.from_bytes(private_key_bytes)
            logger.info("Приватный ключ загружен")
            return keypair
        except DecodeError as e:
            logger.error(f"Ошибка декодирования: {e}")
            raise ValueError(f"Ошибка декодирования: {e}")
        except Exception as e:
            logger.error(f"Ошибка загрузки ключа: {e}")
            raise ValueError(f"Ошибка загрузки ключа: {e}")

    async def get_wallet_balance(self, wallet_address: str) -> float:

        try:
            pubkey = Pubkey.from_string(wallet_address)
            balance_response = self.api_helper.solana_client.get_balance(pubkey)
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1_000_000_000  # Конвертация из lamports в SOL
            logger.info(f"Баланс кошелька {wallet_address}: {balance_sol} SOL")
            return balance_sol
        except Exception as e:
            logger.error(f"Ошибка получения баланса кошелька {wallet_address}: {e}")
            raise

    async def execute_trade(self, token_address: str, tracked_percentage: float, action: str, price: float,
                            max_trade_amount: float) -> str:
        start_time = time.time()

        bot_keypair = await self._load_bot_wallet(self.user)
        bot_wallet_address = str(bot_keypair.pubkey())
        bot_balance = await self.get_wallet_balance(bot_wallet_address)
        if bot_balance <= 0:
            raise ValueError(f"Ваш баланс равен 0")

        # Расчёт bot_amount
        if action == TransactionAction.BUY:
            bot_amount = await self._calculate_buy_amount(tracked_percentage, bot_balance)
            # Ограничиваем bot_amount значением max_trade_amount
            bot_amount = min(bot_amount, max_trade_amount)
            logger.info(
                f"BUY: Ограниченный объём сделки: {bot_amount:.4f} SOL (max_trade_amount: {max_trade_amount:.4f} SOL)")
        else:  # SELL
            # Получаем текущий баланс токенов нашего кошелька
            wallet_token = await self.wallet_token_service.update_wallet_token_balance(
                wallet_address=bot_wallet_address,
                token_address=token_address
            )
            if not wallet_token or wallet_token.balance <= 0:
                raise ValueError(f"Баланс токенов {token_address} равен 0 или не найден")

            our_token_balance = wallet_token.balance
            # Рассчитываем bot_amount как процент от нашего баланса токенов
            bot_amount = (our_token_balance * tracked_percentage) / 100
            if bot_amount <= 0:
                raise ValueError(f"Рассчитанный объём для продажи {bot_amount} некорректен")

            # Проверяем стоимость в SOL, чтобы не превысить max_trade_amount
            bot_amount_in_sol = bot_amount * price
            if bot_amount_in_sol > max_trade_amount:
                bot_amount = max_trade_amount / price
                logger.info(
                    f"SELL: Ограниченный объём сделки: {bot_amount:.4f} токенов (эквивалент {max_trade_amount:.4f} SOL, превысил max_trade_amount)")
            else:
                logger.info(
                    f"SELL: Объём сделки: {bot_amount:.4f} токенов ({tracked_percentage:.2f}% от {our_token_balance} токенов), эквивалент {bot_amount_in_sol:.4f} SOL")

        # Виконання свопу через Jupiter API
        wsol = "So11111111111111111111111111111111111111112"
        input_mint = wsol if action == TransactionAction.BUY else token_address
        output_mint = token_address if action == TransactionAction.BUY else wsol

        try:
            # Використовуємо Jupiter API для виконання свопу
            tx_signature = await self.api_helper.jupiter_api.execute_swap(
                keypair=bot_keypair,  # Передаємо ключ
                input_mint=input_mint,
                output_mint=output_mint,
                amount=bot_amount,  # Кількість у SOL або токенах
                action=action,
                slippage_bps=100  # Додаємо параметр ковзного спреду, якщо потрібно
            )
            end_time = time.time()
            logger.info(
                f"Trade executed: {action} {token_address} for {bot_amount} {'SOL' if action == TransactionAction.BUY else 'tokens'}, time: {end_time - start_time:.4f}s")
            return tx_signature
        except Exception as e:
            logger.error(f"Ошибка выполнения сделки: {e}")
            raise

    async def _calculate_buy_amount(self, tracked_percentage: float, bot_balance: float) -> float:

        bot_amount = (tracked_percentage / 100) * bot_balance
        logger.info(
            f"BUY: Ваш кошелек: баланс {bot_balance:.4f} SOL, покупка на {tracked_percentage:.2f}% = {bot_amount:.4f} SOL")

        min_amount = 0.01
        if bot_amount < min_amount:
            bot_amount = min_amount
            logger.warning(f"Сумма для покупки ({bot_amount:.4f} SOL) меньше минимальной, установлено {min_amount} SOL")
        if bot_amount > bot_balance:
            raise ValueError(f"Недостаточно средств: требуется {bot_amount:.4f} SOL, доступно {bot_balance:.4f} SOL")
        return bot_amount

    async def _calculate_sell_amount(self, token_address: str, tracked_percentage: float) -> float:
        """Рассчитывает сумму для продажи и проверяет ограничения."""
        if token_address not in self.token_balances or self.token_balances[token_address] <= 0:
            raise ValueError(f"SELL: Нет токенов {token_address} для продажи")
        bot_token_balance = self.token_balances[token_address]
        bot_amount = (tracked_percentage / 100) * bot_token_balance
        logger.info(
            f"SELL: Ваш кошелек: баланс токенов {bot_token_balance}, продажа на {tracked_percentage:.2f}% = {bot_amount} токенов")

        if bot_amount > bot_token_balance:
            raise ValueError(f"Недостаточно токенов: требуется {bot_amount}, доступно {bot_token_balance}")
        return bot_amount

    async def process_transaction(self, transaction_details: Dict, wallet_address: str):
        try:
            if transaction_details["transaction_action"] in [TransactionAction.BUY, TransactionAction.SELL]:
                token_address = transaction_details["token_address"]
                action = transaction_details["transaction_action"]

                # Получаем баланс SOL отслеживаемого кошелька
                tracked_balance = await self.get_wallet_balance(wallet_address)
                if tracked_balance <= 0:
                    raise ValueError(f"Баланс отслеживаемого кошелька {wallet_address} равен 0")

                # Получаем баланс нашего депозита (предполагается, что у нас есть метод для нашего кошелька)
                our_deposit = await self.get_wallet_balance(
                    self.our_wallet_address)  # Предполагаемый атрибут our_wallet_address
                if our_deposit <= 0:
                    raise ValueError(f"Баланс нашего депозита равен 0")

                # Инициализация переменных
                tracked_percentage = 0.0

                if action == TransactionAction.BUY:
                    # Для BUY: Сколько SOL потрачено на покупку
                    tracked_amount = transaction_details["sell_amount"]  # SOL, потраченные на покупку
                    tracked_percentage = (tracked_amount / tracked_balance) * 100
                    logger.info(
                        f"BUY: Отслеживаемый кошелек потратил {tracked_amount:.4f} SOL ({tracked_percentage:.2f}% от баланса {tracked_balance:.4f} SOL)")

                    # Сохраняем количество купленных токенов в token_balances
                    bought_amount = transaction_details["buy_amount"]
                    if token_address in self.token_balances:
                        self.token_balances[token_address] += bought_amount
                    else:
                        self.token_balances[token_address] = bought_amount
                    logger.info(
                        f"Токен {token_address}: куплено {bought_amount}, новый баланс токенов {self.token_balances[token_address]}")

                elif action == TransactionAction.SELL:
                    # Получаем текущий баланс токенов на отслеживаемом кошельке через WalletTokenService
                    wallet_token = await self.wallet_token_service.update_wallet_token_balance(
                        wallet_address=wallet_address,
                        token_address=token_address
                    )
                    if not wallet_token:
                        logger.warning(
                            f"Не удалось получить баланс для {token_address}, токен-аккаунт не найден или ошибка")
                        return

                    current_tracked_balance = wallet_token.balance
                    logger.info(
                        f"Текущий баланс отслеживаемого кошелька для {token_address}: {current_tracked_balance}")

                    # Рассчитываем ранее купленное количество (из self.token_balances)
                    total_bought = self.token_balances.get(token_address, 0.0)
                    if total_bought <= 0:
                        logger.warning(f"SELL: Нет данных о купленных токенах для {token_address}, пропускаем")
                        return

                    # Рассчитываем проданное количество
                    sold_amount = total_bought - current_tracked_balance
                    if sold_amount <= 0:
                        logger.warning(f"SELL: Отслеживаемый кошелёк не продал токены или баланс не изменился")
                        return

                    # Рассчитываем процент продажи
                    tracked_percentage = (sold_amount / total_bought) * 100
                    logger.info(
                        f"SELL: Отслеживаемый кошелек продал {sold_amount} токенов ({tracked_percentage:.2f}% от купленных {total_bought})")

                    # Обновляем баланс токенов после продажи
                    self.token_balances[token_address] -= sold_amount
                    if self.token_balances[token_address] <= 0:
                        del self.token_balances[token_address]
                    logger.info(
                        f"Токен {token_address}: продано {sold_amount}, новый баланс токенов {self.token_balances.get(token_address, 0)}")

                # Ограничиваем tracked_percentage значением 5%
                max_allowed_percentage = min(tracked_percentage, 5.0)
                logger.info(
                    f"Ограниченный процент для сделки: {max_allowed_percentage:.2f}% (из {tracked_percentage:.2f}%)")

                # Рассчитываем максимальную сумму для нашей сделки (не более 5% депозита)
                max_trade_amount = (our_deposit * max_allowed_percentage) / 100
                logger.info(
                    f"Максимальная сумма сделки: {max_trade_amount:.4f} SOL (5% от депозита {our_deposit:.4f} SOL)")

                # Выполняем сделку, передавая ограниченную сумму
                tx_signature = await self.execute_trade(
                    token_address=token_address,
                    tracked_percentage=max_allowed_percentage,  # Передаем ограниченный процент
                    action=action,
                    price=transaction_details["price"],
                    max_trade_amount=max_trade_amount,  # Передаем максимальную сумму
                )
                transaction_details["transaction_hash"] = tx_signature
                await self.save_bot_transaction(transaction_details)

        except Exception as e:
            logger.error(f"Ошибка обработки транзакции: {e}")
            raise

    async def save_bot_transaction(self, transaction_details: Dict):
        try:
            async with self.session_factory() as session:
                new_transaction = MyWalletTransaction(
                    transaction_hash=transaction_details["transaction_hash"],
                    transaction_action=transaction_details["transaction_action"],
                    status=TransactionStatus.SUCCESS,
                    token_address=transaction_details["token_address"],
                    token_symbol=transaction_details["token_symbol"],
                    buy_amount=transaction_details["buy_amount"] if transaction_details[
                                                                        "transaction_action"] == TransactionAction.BUY else None,
                    sell_amount=transaction_details["sell_amount"] if transaction_details[
                                                                          "transaction_action"] == TransactionAction.SELL else None,
                    price=transaction_details["price"],
                    timestamp=func.now()
                )
                session.add(new_transaction)
                await session.commit()
                logger.info(f"Transaction saved: {transaction_details['transaction_hash']}")
        except Exception as e:
            logger.error(f"Ошибка сохранения транзакции: {e}")
            raise

    async def start_tracking_and_copy(self, wallet_address: str, interval_seconds: int = 5):
        """
        Запускает отслеживание кошелька с выполнением сделок.
        """
        try:
            # Устанавливаем статус ACTIVE
            await self.tracked_wallet_service.update_wallet_status(wallet_address, FollowMode.COPY)
            logger.info(f"Запуск отслеживания кошелька {wallet_address} с интервалом {interval_seconds} секунд")
            while True:
                new_transactions = await self.tracked_wallet_service.update_wallet_data(wallet_address)
                if new_transactions is None:
                    logger.info(f"За последнее время для кошелька {wallet_address} не найдено новых транзакций")
                    new_transactions = []
                for tx in new_transactions:
                    if tx.get("transaction_action") in [TransactionAction.BUY, TransactionAction.SELL]:
                        await self.process_transaction(tx, wallet_address)
                logger.info(f"Проверено транзакций: {len(new_transactions)} для кошелька {wallet_address}")
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            await self.tracked_wallet_service.update_wallet_status(wallet_address, FollowMode.MONITOR)
            logger.info(f"Отслеживание кошелька {wallet_address} остановлено")
        except Exception as e:
            await self.tracked_wallet_service.update_wallet_status(wallet_address, FollowMode.MONITOR)
            logger.error(f"Ошибка отслеживания кошелька {wallet_address}: {e}")
            raise

    async def get_is_tracking(self, wallet_address: str, user: User) -> bool:
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
                raise ValueError(f"Кошелек {wallet_address} не найден для пользователя {user.id}")
            return tracked_wallet.is_tracking

    async def start_tracking_without_any_actions(self, wallet_address: str, user: User, interval_seconds: int ):

        await self.tracked_wallet_service.update_wallet_status(wallet_address, FollowMode.MONITOR)
        logger.info(
            f"Запуск пассивного отслеживания кошелька {wallet_address} с интервалом {interval_seconds} секунд")

        try:

            while True:

                is_tracking = await self.get_is_tracking(wallet_address, user)
                if not is_tracking:
                    logger.info(
                        f"Пассивное отслеживание кошелька {wallet_address} остановлено из-за is_tracking = False")
                    break

                new_transactions = await self.tracked_wallet_service.update_wallet_data(wallet_address)

                if new_transactions is None:
                    logger.info(f"За последнее время для кошелька {wallet_address} не найдено новых транзакций")
                    new_transactions = []
                logger.info(f"Проверено транзакций: {len(new_transactions)} для кошелька {wallet_address}")
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            await self.tracked_wallet_service.update_wallet_status(wallet_address, FollowMode.MONITOR)
            logger.info(f"Пассивное отслеживание кошелька {wallet_address} остановлено")
        except Exception as e:
            await self.tracked_wallet_service.update_wallet_status(wallet_address, FollowMode.MONITOR)
            logger.error(f"Ошибка пассивного отслеживания кошелька {wallet_address}: {e}")
            raise


    async def get_active_user_wallet(self, user: User) -> str:
        try:
            async with self.session_factory() as session:

                result = await session.execute(
                    select(BotWallet)
                    .filter(BotWallet.user_id == user.id, BotWallet.status == True)
                )
                active_wallet = result.scalars().first()

                if not active_wallet:
                    logger.error(f"Активний гаманець для користувача {user.id} не знайдено")
                    raise HTTPException(
                        status_code=404,
                        detail="Активний гаманець не знайдено"
                    )

                logger.info(f"Активний гаманець для користувача {user.id}: {active_wallet.private_key}")
                return active_wallet.private_key

        except Exception as e:
            logger.error(f"Помилка при отриманні активного гаманця для користувача {user.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Помилка при отриманні активного гаманця: {str(e)}"
            )
