from typing import Optional, Dict, Set
import asyncio

from dns.dnssec import PublicKey
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from solders.pubkey import Pubkey
import sqlite3
import aiosqlite

from api.routers.tracked_wallet_route import tracked_wallet_router
from api.solana_api import SolanaAPI
from core.models.my_wallet_transaction import TransactionAction, TransactionStatus, MyWalletTransaction
from core.models.tracked_wallet import TrackedWallet
from decouple import config
import base58
import logging
import time

logger = logging.getLogger(__name__)

# Импортируем RaydiumAPI и TrackedWalletService
from api.raydium_api import RaydiumAPI
from core.service.tracked_wallet_service import WalletService



class BotWalletService:
    def __init__(self):
        """
        Инициализация сервиса бота.
        """
        quicknode_endpoint = config("QUICKNODE_ENDPOINT")
        self.solana_client = Client(quicknode_endpoint)
        self.solana_api = SolanaAPI()
        self.tracked_wallet_service = WalletService()
        self.bot_keypair = self._load_bot_wallet()
        self.raydium_api = RaydiumAPI(rpc_endpoint=quicknode_endpoint)
        self.processed_transactions: Set[str] = set()
        self.token_balances: Dict[str, float] = {}  # Т


    def _load_bot_wallet(self) -> Keypair:
        try:
            private_key_base58 = config("PHANTOM_PRIVATE_KEY", default=None)
            if not private_key_base58:
                logger.error("PHANTOM_PRIVATE_KEY не найден")
                raise ValueError("PHANTOM_PRIVATE_KEY не найден")
            private_key_bytes = base58.b58decode(private_key_base58.strip())
            if len(private_key_bytes) != 64:
                raise ValueError(f"Ожидается 64 байта")
            keypair = Keypair.from_bytes(private_key_bytes)
            logger.info("Приватный ключ загружен")
            return keypair
        except base58.Base58DecodeError as e:
            logger.error(f"Ошибка декодирования: {e}")
            raise ValueError(f"Ошибка декодирования: {e}")
        except Exception as e:
            logger.error(f"Ошибка загрузки ключа: {e}")
            raise ValueError(f"Ошибка загрузки ключа: {e}")


    async def get_wallet_balance(self, wallet_address: str) -> float:

        try:
            pubkey = Pubkey.from_string(wallet_address)
            balance_response = await self.solana_client.get_balance(pubkey)
            balance_lamports = balance_response.value
            balance_sol = balance_lamports / 1_000_000_000  # Конвертация из lamports в SOL
            logger.info(f"Баланс кошелька {wallet_address}: {balance_sol} SOL")
            return balance_sol
        except Exception as e:
            logger.error(f"Ошибка получения баланса кошелька {wallet_address}: {e}")
            raise

    async def execute_trade(self, token_address: str, tracked_amount: float, tracked_percentage: float, action: str,
                            price: float, tracked_wallet_address: str) -> str:
        start_time = time.time()

        # Получаем баланс вашего кошелька
        bot_wallet_address = str(self.bot_keypair.public_key)
        bot_balance = await self.get_wallet_balance(bot_wallet_address)
        if bot_balance <= 0:
            raise ValueError(f"Ваш баланс равен 0")

        # Для BUY: Используем процент от баланса SOL
        # Для SELL: Используем процент от баланса токенов
        if action == TransactionAction.BUY:
            bot_amount = (tracked_percentage / 100) * bot_balance
            logger.info(
                f"BUY: Ваш кошелек: баланс {bot_balance:.4f} SOL, покупка на {tracked_percentage:.2f}% = {bot_amount:.4f} SOL")
        else:  # SELL
            if token_address not in self.token_balances or self.token_balances[token_address] <= 0:
                raise ValueError(f"SELL: Нет токенов {token_address} для продажи")
            bot_token_balance = self.token_balances[token_address]
            bot_amount = (tracked_percentage / 100) * bot_token_balance
            logger.info(
                f"SELL: Ваш кошелек: баланс токенов {bot_token_balance}, продажа на {tracked_percentage:.2f}% = {bot_amount} токенов")

        # Ограничение для теста
        if action == TransactionAction.BUY:
            min_amount = 0.01  # Минимальная сумма для теста
            if bot_amount < min_amount:
                bot_amount = min_amount
                logger.warning(
                    f"Сумма для покупки ({bot_amount:.4f} SOL) меньше минимальной, установлено {min_amount} SOL")
            if bot_amount > bot_balance:
                raise ValueError(
                    f"Недостаточно средств: требуется {bot_amount:.4f} SOL, доступно {bot_balance:.4f} SOL")
        else:
            if bot_amount > bot_token_balance:
                raise ValueError(f"Недостаточно токенов: требуется {bot_amount}, доступно {bot_token_balance}")

        wsol = "So11111111111111111111111111111111111111112"
        input_mint = wsol if action == TransactionAction.BUY else token_address
        output_mint = token_address if action == TransactionAction.BUY else wsol

        try:
            tx_signature = await self.raydium_api.execute_swap(
                self.bot_keypair, input_mint, output_mint, bot_amount, action, price
            )
            end_time = time.time()
            logger.info(
                f"Trade executed: {action} {token_address} for {bot_amount} {'SOL' if action == TransactionAction.BUY else 'tokens'}, time: {end_time - start_time:.4f}s")
            return tx_signature
        except Exception as e:
            logger.error(f"Ошибка выполнения сделки: {e}")
            raise

    async def process_transaction(self, transaction_details: Dict, wallet_address: str):
        try:
            if transaction_details["transaction_action"] in [TransactionAction.BUY, TransactionAction.SELL]:
                token_address = transaction_details["token_address"]
                action = transaction_details["transaction_action"]

                # Получаем баланс SOL отслеживаемого кошелька
                tracked_balance = await self.get_wallet_balance(wallet_address)
                if tracked_balance <= 0:
                    raise ValueError(f"Баланс отслеживаемого кошелька {wallet_address} равен 0")

                # Инициализация переменных
                tracked_percentage = 0.0
                tracked_amount = 0.0

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
                    # Для SELL: Сколько токенов продано и какой процент от ранее купленного
                    tracked_amount = transaction_details["sell_amount"]  # Токены, проданные
                    if token_address not in self.token_balances or self.token_balances[token_address] <= 0:
                        logger.warning(f"SELL: Нет данных о купленных токенах для {token_address}, пропускаем")
                        return
                    total_bought = self.token_balances[token_address]
                    tracked_percentage = (tracked_amount / total_bought) * 100
                    logger.info(
                        f"SELL: Отслеживаемый кошелек продал {tracked_amount} токенов ({tracked_percentage:.2f}% от купленных {total_bought})")

                    # Обновляем баланс токенов после продажи
                    self.token_balances[token_address] -= tracked_amount
                    if self.token_balances[token_address] <= 0:
                        del self.token_balances[token_address]
                    logger.info(
                        f"Токен {token_address}: продано {tracked_amount}, новый баланс токенов {self.token_balances.get(token_address, 0)}")

                # Выполняем сделку, передавая процент
                tx_signature = await self.execute_trade(
                    token_address=token_address,
                    tracked_amount=tracked_amount,
                    tracked_percentage=tracked_percentage,  # Передаем процент
                    action=action,
                    price=transaction_details["price"],
                    tracked_wallet_address=wallet_address
                )
                transaction_details["transaction_hash"] = tx_signature
                await self.save_bot_transaction(transaction_details)

        except Exception as e:
            logger.error(f"Ошибка обработки транзакции: {e}")
            raise

    async def save_bot_transaction(self, transaction_details: Dict):
        try:
            async with self.db_helper.session_factory() as session:
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

    async def start_tracking(self, wallet_address: str):
        try:
            new_transactions = await self.tracked_wallet_service.update_wallet_data(wallet_address)
            for tx in new_transactions:
                if tx.get("transaction_action")==TransactionAction.BUY or tx.get("transaction_action")==TransactionAction.SELL:
                    await self.process_transaction(tx, wallet_address)
        except Exception as e:
            logger.error(f"Ошибка отслеживания: {e}")
            raise
