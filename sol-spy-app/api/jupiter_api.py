from typing import Dict
import requests
import base64
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig
import logging
import time
import asyncio

logger = logging.getLogger(__name__)

class JupiterAPI:
    def __init__(self,rpc_endpoint: str ,jupiter_api_endpoint: str = "https://lite-api.jup.ag/swap/v1"):
        self.solana_client = AsyncClient(rpc_endpoint)
        self.jupiter_api_endpoint = jupiter_api_endpoint

    async def get_swap_quote_for_buy(self, input_mint: str, output_mint: str, amount: float) -> Dict:
        url = f"{self.jupiter_api_endpoint}/quote"
        headers = {
            'Accept': 'application/json'
        }

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": int(amount * 10 ** 6),
            "slippageBps": str(300)
        }
        try:
            response = requests.request("GET", url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get swap quote: {e}")
            raise

    async def get_swap_quote_for_sell(self, input_mint: str, output_mint: str, amount: float) -> Dict:
        url = f"{self.jupiter_api_endpoint}/quote"
        headers = {
            'Accept': 'application/json'
        }

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": str(7000)
        }
        try:
            response = requests.request("GET", url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get swap quote: {e}")
            raise

    async def execute_swap_for_buy(self, keypair: Keypair, input_mint: str, output_mint: str, amount: float, action: str) -> str:
        start_time = time.time()

        # Отримуємо котирування
        quote = await self.get_swap_quote_for_buy(input_mint, output_mint, amount)
        if not quote or "data" not in quote:
            raise ValueError("Failed to get swap quote from Jupiter API")

        # Вибираємо першу котировку і перевіряємо outAmount
        quote_data = quote["data"][0]
        expected_out_amount = float(quote_data["outAmount"]) / 10 ** 6  # Конвертація в людські одиниці
        logger.info(f"Expected output amount: {expected_out_amount} {output_mint}")

        swap_url = f"{self.jupiter_api_endpoint}/swap"
        swap_payload = {
            "quoteResponse": quote_data,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            # "feeAccount": str(fee_account_pubkey)  # Опціонально, якщо потрібен окремий акаунт для комісій
        }
        try:
            swap_response = requests.post(swap_url, json=swap_payload, timeout=5)
            swap_response.raise_for_status()
            response_data = swap_response.json()
            if "swapTransaction" not in response_data:
                raise ValueError("No swapTransaction in response")
            tx_data = response_data["swapTransaction"]
        except requests.RequestException as e:
            logger.error(f"Failed to get swap transaction: {e}")
            raise

        # Декодуємо транзакцію з base64
        transaction_buffer = base64.b64decode(tx_data)

        # Десеріалізація транзакції
        transaction = VersionedTransaction.from_bytes(transaction_buffer)

        # Отримуємо recent_blockhash
        recent_blockhash_response = await self.solana_client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_response.value.blockhash

        # Оновлюємо recent_blockhash
        transaction.message.recent_blockhash = recent_blockhash

        # Налаштовуємо конфігурацію відправки
        config = RpcSendTransactionConfig(
            skip_preflight=True,
            max_retries=3,
            preflight_commitment="confirmed",
            priority_fee=100000
        )

        # Відправляємо транзакцію з ключем для підпису
        tx_signature = await self.solana_client.send_transaction(
            transaction=transaction,
            signers=[keypair],
            config=config
        )
        end_time = time.time()
        logger.info(
            f"Swap executed: {action} {output_mint} for {amount} tokens, signature: {tx_signature.value}, time: {end_time - start_time:.4f} seconds")
        return str(tx_signature.value)


    async def execute_swap_for_sell(self, keypair: Keypair, input_mint: str, output_mint: str, amount: float, action: str) -> str:
        start_time = time.time()

        # Отримуємо котирування
        quote = await self.get_swap_quote_for_sell(input_mint, output_mint, amount)
        if not quote or "data" not in quote:
            raise ValueError("Failed to get swap quote from Jupiter API")

        # Вибираємо першу котировку і перевіряємо outAmount
        quote_data = quote["data"][0]
        expected_out_amount = float(quote_data["outAmount"])
        logger.info(f"Expected output amount: {expected_out_amount} {output_mint}")

        swap_url = f"{self.jupiter_api_endpoint}/swap"
        swap_payload = {
            "quoteResponse": quote_data,
            "userPublicKey": str(keypair.pubkey()),
            "wrapAndUnwrapSol": True,
            # "feeAccount": str(fee_account_pubkey)  # Опціонально, якщо потрібен окремий акаунт для комісій
        }
        try:
            swap_response = requests.post(swap_url, json=swap_payload, timeout=5)
            swap_response.raise_for_status()
            response_data = swap_response.json()
            if "swapTransaction" not in response_data:
                raise ValueError("No swapTransaction in response")
            tx_data = response_data["swapTransaction"]
        except requests.RequestException as e:
            logger.error(f"Failed to get swap transaction: {e}")
            raise

        # Декодуємо транзакцію з base64
        transaction_buffer = base64.b64decode(tx_data)

        # Десеріалізація транзакції
        transaction = VersionedTransaction.from_bytes(transaction_buffer)

        # Отримуємо recent_blockhash
        recent_blockhash_response = await self.solana_client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_response.value.blockhash

        # Оновлюємо recent_blockhash
        transaction.message.recent_blockhash = recent_blockhash

        # Налаштовуємо конфігурацію відправки
        config = RpcSendTransactionConfig(
            skip_preflight=True,
            max_retries=3,
            preflight_commitment="confirmed",
            priority_fee=100000
        )

        # Відправляємо транзакцію з ключем для підпису
        tx_signature = await self.solana_client.send_transaction(
            transaction=transaction,
            signers=[keypair],
            config=config
        )
        end_time = time.time()
        logger.info(
            f"Swap executed: {action} {output_mint} for {amount} tokens, signature: {tx_signature.value}, time: {end_time - start_time:.4f} seconds")
        return str(tx_signature.value)

