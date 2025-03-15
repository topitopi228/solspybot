from decimal import Decimal
from typing import TYPE_CHECKING, Dict

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from core.models.wallet_transaction import TransactionAction, TransactionStatus, WalletTransaction


class SolanaAPI:
    def __init__(self, endpoint: str = "https://api.mainnet-beta.solana.com"):
        self.client = AsyncClient(endpoint)
        # Инициализация Bitquery API или утилит
        from api.bitquery_api import BitqueryAPI  # Импорт отдельного класса
        self.bitquery = BitqueryAPI()

    async def get_balance(self, wallet_address: str) -> float:
        try:
            public_key = Pubkey.from_string(wallet_address)
            response = await self.client.get_balance(public_key)
            lamports = response.value
            return lamports / 1_000_000_000
        except Exception as e:
            raise ValueError(f"Failed to get balance for {wallet_address}: {e}")

    async def get_wallet_transactions(self, wallet_address: str, limit: int = 10):
        try:
            public_key = Pubkey.from_string(wallet_address)
            response = await self.client.get_signatures_for_address(public_key, limit=limit)
            return response.value
        except Exception as e:
            raise ValueError(f"Failed to fetch transactions for {wallet_address}: {e}")

    async def get_transaction_details(self, signature: Signature) -> Dict :

        """
        Получает детали транзакции по её подписи, включая тип транзакции, адрес токена, символ токена, количество базового и котируемого токена, и цену в SOL,
        используя только Bitquery для дополнительной информации.
        """
        transaction_hash = str(signature)
        token_address = None
        token_symbol = None
        buy_amount = None  # Количество базового токена (купленного/проданного)
        sell_amount = None  # Количество котируемого токена (например, SOL)
        price = None
        transaction_action = TransactionAction.TRANSFER
        transaction_info=None
        dex_name=None

        # Используем Bitquery для получения всех данных, если доступен
        if self.bitquery:

            # Определяем тип транзакции
            transaction_info = await self.bitquery.get_transaction_info(transaction_hash)
            if transaction_info.get("transaction_type") == "buy":
                transaction_action = TransactionAction.BUY
            elif transaction_info.get("transaction_type") == "sell":
                transaction_action = TransactionAction.SELL
            else:
                transaction_action = TransactionAction.TRANSFER

                # Получаем цену, если символ токена известен
            price = await self.bitquery.get_token_price_in_sol(transaction_info.get("token_address"))

        else:
            # Если Bitquery недоступен, возвращаем значения по умолчанию
            token_symbol = "Unknown"
            buy_amount = 0.0
            sell_amount =0.0
            price = 0.0
            dex_name="Unknown"
            transaction_action = TransactionAction.TRANSFER

        return {
            "transaction_hash": transaction_hash,
            "transaction_action": transaction_action,
            "token_address": transaction_info.get("token_address"),
            "token_symbol": transaction_info.get("token_symbol"),
            "buy_amount": transaction_info.get("buy_amount"),
            "sell_amount": transaction_info.get("sell_amount"),
            "transfer_amount": transaction_info.get("transfer_amount"),
            "dex_name": transaction_info.get("dex_name"),
            "price": price
        }

    async def close(self):
        """
        Закрывает соединение с клиентом Solana и Bitquery.
        """
        await self.client.close()
        await self.bitquery.close()
