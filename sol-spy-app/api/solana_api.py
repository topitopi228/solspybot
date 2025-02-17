from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature


class SolanaAPI:
    def __init__(self, endpoint: str = "https://api.mainnet-beta.solana.com"):
        self.client = AsyncClient(endpoint)

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

    async def get_transaction_details(self, signature: Signature):
        """
        Получает детали транзакции по её подписи.
        """
        response = await self.client.get_transaction(signature)
        transaction_data = response.value

        # Анализируем инструкции
        instructions = transaction_data['transaction']['message']['instructions']

        # Примерная логика для определения типа транзакции (например, на основе адреса программы)
        for instruction in instructions:
            program_id = instruction['programId']

            # Предположим, что для покупки или продажи используется конкретная программа, например, токен-своп
            # В реальном коде нужно будет учитывать конкретные программы или операции
            if program_id == "TokenSwapProgramId":  # замените на фактический ID программы
                return "Token Swap (Buying/Selling)"
            elif program_id == "TokenTransferProgramId":  # замените на фактический ID программы
                return "Token Transfer"

        return "Unknown Transaction Type"

    async def close(self):
        """
        Закрывает соединение с клиентом.
        """
        await self.client.close()