from typing import Optional, Dict
import asyncio
import requests
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.solders import Transaction
from solders.transaction import Transaction as SolanaTransaction
from solders.rpc.config import RpcSendTransactionConfig
from solders.instruction import Instruction
import logging
import time
import json

from core.models.my_wallet_transaction import MyWalletTransaction

logger = logging.getLogger(__name__)

class RaydiumAPI:
    def __init__(self, rpc_endpoint: str, raydium_api_endpoint: str = "https://api.raydium.io/v1"):
        """
        Инициализация API для взаимодействия с Raydium Trade API и Solana RPC.

        Args:
            rpc_endpoint: URL RPC-ноды Solana (загружается из .env в BotWalletService)
            raydium_api_endpoint: URL Raydium Trade API
        """
        self.solana_client = Client(rpc_endpoint)
        self.raydium_api_endpoint = raydium_api_endpoint

    async def get_swap_quote(self, input_mint: str, output_mint: str, amount: float, slippage_bps: int = 100) -> Dict:
        """
        Получает котировку для свопа через Raydium Trade API.

        Args:
            input_mint: Адрес входного токена (например, WSOL: "So11111111111111111111111111111111111111112")
            output_mint: Адрес выходного токена (например, целевой токен)
            amount: Количество для свопа (в нативных единицах)
            slippage_bps: Допустимое проскальзывание в базовых пунктах (по умолчанию 100 = 1%)

        Returns:
            Dict: Данные котировки, включая инструкции для свопа
        """
        url = f"{self.raydium_api_endpoint}/swap/quote"
        payload = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),  # Конвертируем в строку для точности
            "slippageBps": slippage_bps
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get swap quote: {e}")
            raise

    async def execute_swap(self, keypair: Keypair, input_mint: str, output_mint: str, amount: float, action: str,
                           price: float, slippage_bps: int = 100) -> str:
        """
        Выполняет своп (покупка/продажа) через Raydium Trade API и Solana RPC.

        Args:
            keypair: Ключевой пары кошелька (Phantom-кошелек)
            input_mint: Адрес входного токена (WSOL для покупки, целевой токен для продажи)
            output_mint: Адрес выходного токена (целевой токен для покупки, WSOL для продажи)
            amount: Количество для свопа (в нативных единицах)
            action: Тип действия ('BUY' или 'SELL')
            price: Цена токена в SOL
            slippage_bps: Допустимое проскальзывание в базовых пунктах

        Returns:
            str: Подпись транзакции (Base58)
        """
        start_time = time.time()  # Измеряем время для оптимизации скорости

        # Получаем котировку для свопа
        quote = await self.get_swap_quote(input_mint, output_mint, amount, slippage_bps)
        if not quote or "transaction" not in quote:
            raise ValueError("Failed to get swap quote from Raydium API")

        # Извлекаем данные транзакции из ответа API
        transaction_data = quote["transaction"]
        transaction_buffer = bytes.fromhex(transaction_data["transaction"])  # Предполагаем, что данные в hex-формате

        # Создаем инструкцию из данных Raydium
        instruction = Instruction(
            program_id=Pubkey.from_string(
                transaction_data.get("programId", "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")),
            accounts=[Pubkey.from_string(acc["pubkey"]) for acc in transaction_data.get("accounts", [])],
            data=transaction_buffer
        )

        # Получаем recent_blockhash с QuickNode
        recent_blockhash = await self.solana_client.get_latest_blockhash()

        # Создаем и подписываем транзакцию
        transaction = Transaction(recent_blockhash=recent_blockhash.value.blockhash)
        transaction.add(instruction)
        transaction.sign(keypair)

        # Настраиваем конфигурацию отправки с приоритетом для повышения скорости
        config = RpcSendTransactionConfig(
            skip_preflight=True,
            max_retries=3,
            preflight_commitment="confirmed",
            priority_fee=100000  # Пример приоритета, можно настроить динамически
        )

        # Отправляем транзакцию через QuickNode
        tx_signature = await self.solana_client.send_transaction(transaction, config=config)
        end_time = time.time()
        logger.info(
            f"Swap executed: {action} {output_mint} for {amount} tokens, signature: {tx_signature.value}, time: {end_time - start_time:.4f} seconds")
        return str(tx_signature.value)