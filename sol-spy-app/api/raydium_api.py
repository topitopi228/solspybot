from typing import  Dict

import requests

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from solders.solders import Transaction

from solders.rpc.config import RpcSendTransactionConfig
from solders.instruction import Instruction
import logging
import time


logger = logging.getLogger(__name__)


class RaydiumAPI:
    def __init__(self, rpc_endpoint: str, raydium_api_endpoint: str = "https://api.raydium.io/v1"):

        self.solana_client = AsyncClient(rpc_endpoint)
        self.raydium_api_endpoint = raydium_api_endpoint

    async def get_swap_quote(self, input_mint: str, output_mint: str, amount: float, slippage_bps: int = 100) -> Dict:

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
                           slippage_bps: int = 100) -> str:

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
        recent_blockhash = self.solana_client.get_latest_blockhash()

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
        tx_signature = self.solana_client.send_transaction(transaction, config=config)
        end_time = time.time()
        logger.info(
            f"Swap executed: {action} {output_mint} for {amount} tokens, signature: {tx_signature.value}, time: {end_time - start_time:.4f} seconds")
        return str(tx_signature.value)
