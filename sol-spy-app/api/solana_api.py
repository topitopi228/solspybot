from decimal import Decimal
from typing import TYPE_CHECKING

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature

if TYPE_CHECKING:
    from core.models.wallet_transaction import TransactionAction, TransactionStatus


class TransactionDetails:
    def __init__(self, transaction_hash, transaction_action, token_address, token_symbol, base_amount, quote_amount, price):
        self.transaction_hash = str(transaction_hash)
        self.transaction_action = transaction_action
        self.token_address = token_address
        self.token_symbol = token_symbol
        self.base_amount = base_amount
        self.quote_amount = quote_amount
        self.price = price


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
            print(response)
            return response.value
        except Exception as e:
            raise ValueError(f"Failed to fetch transactions for {wallet_address}: {e}")

    async def get_transaction_details(self, signature: Signature) -> TransactionDetails:

        """
        Получает детали транзакции по её подписи, включая тип транзакции, адрес токена, символ токена, количество базового и котируемого токена, и цену в SOL,
        используя только Bitquery для дополнительной информации.
        """
        transaction_hash = str(signature)
        token_address = None
        token_symbol = None
        base_amount = None  # Количество базового токена (купленного/проданного)
        quote_amount = None  # Количество котируемого токена (например, SOL)
        price = None
        transaction_action = TransactionAction.TRANSFER

        # Используем Bitquery для получения всех данных, если доступен
        if self.bitquery:
            # Получаем адрес токена, базовое количество и котируемое количество через Bitquery
            token_address, base_amount, quote_amount = await self.bitquery.get_token_details(transaction_hash)

            # Определяем тип транзакции
            bitquery_type = await self.bitquery.get_transaction_type(transaction_hash)
            print(bitquery_type, "vs,fwfpwfpwefwefwefqpfmqfpqwmwfpqfkmwepkrmvwkpveq")
            print(bitquery_type)
            if bitquery_type == "buy":
                transaction_action = TransactionAction.BUY
            elif bitquery_type == "sell":
                transaction_action = TransactionAction.SELL
            else:
                transaction_action = TransactionAction.TRANSFER

            # Получаем символ токена, если адрес токена найден
            if token_address:
                token_symbol = await self.bitquery.get_token_symbol(token_address)
                # Получаем цену, если символ токена известен
                price = await self.bitquery.get_token_price_in_sol(
                    token_symbol) if token_symbol != "Unknown" else None
            else:
                token_symbol = "Unknown"
                base_amount = None
                quote_amount = None
                price = None
        else:
            # Если Bitquery недоступен, возвращаем значения по умолчанию
            token_symbol = "Unknown"
            base_amount = None
            quote_amount = None
            price = None
            transaction_action = TransactionAction.TRANSFER

        return TransactionDetails(
            transaction_hash=transaction_hash,
            transaction_action=transaction_action,
            token_address=token_address,
            token_symbol=token_symbol,
            base_amount=base_amount,  # Количество базового токена
            quote_amount=quote_amount,  # Количество котируемого токена
            price=price
        )

    async def close(self):
        """
        Закрывает соединение с клиентом Solana и Bitquery.
        """
        await self.client.close()
        await self.bitquery.close()
