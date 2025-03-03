from typing import Optional, Union
import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()

class BitqueryAPI:
    def __init__(self, endpoint: str = "https://graphql.bitquery.io/", api_token: str = None):
        """
        Инициализирует клиента Bitquery API с эндпоинтом и токеном для аутентификации.

        Args:
            endpoint (str): URL эндпоинта Bitquery (по умолчанию https://graphql.bitquery.io/)
            api_token (str, optional): Токен доступа Bitquery. Если не указан, берется из переменной окружения.

        Raises:
            ValueError: Если API токен не указан или некорректен.
        """
        # Получаем токен из переменной окружения, если он не передан явно
        self.api_token = api_token or os.getenv("BITQUERY_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "API токен Bitquery не указан. Укажите его в конструкторе или в переменной окружения BITQUERY_API_TOKEN.")

        # Проверяем формат токена (убираем лишние символы, если они есть)
        self.api_token = self.api_token.strip()
        if not self.api_token:
            raise ValueError("API токен Bitquery пуст или некорректен.")

        logger.info(f"Инициализация Bitquery API с токеном: {self.api_token[:5]}... (сокрыт для безопасности)")

        # Настраиваем транспорт с заголовком для аутентификации
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        self.transport = AIOHTTPTransport(url=endpoint, headers=headers)
        self.client = Client(transport=self.transport, fetch_schema_from_transport=True)

    async def get_token_symbol(self, token_address: str) -> str:
        query = gql(
            """
            query MyQuery($tokenAddress: String!) {
              Solana {
                Tokens(limit: { count: 1 }, where: {Address: {is: $tokenAddress}}) {
                  Token {
                    Symbol
                  }
                  Address
                }
              }
            }
            """
        )
        try:
            variables = {"tokenAddress": token_address}
            result = await self.client.execute_async(query, variable_values=variables)
            tokens = result.get('Solana', {}).get('Tokens', [])
            for token in tokens:
                if token['Address'] == token_address:
                    logger.info(f"Найден символ токена {token['Token']['Symbol']} для адреса {token_address}")
                    return token['Token']['Symbol']
            logger.warning(f"Символ токена для {token_address} не найден")
            return "Unknown"
        except Exception as e:
            logger.error(f"Ошибка при получении символа токена для {token_address}: {e}")
            return "Unknown"

    async def get_token_price_in_sol(self, token_symbol: str) -> Optional[float]:
        query = gql(
            """
            query MyQuery($tokenSymbol: String!) {
              Solana {
                DEXTrades(limit: { count: 1 }, where: {Trade: {Currency: {Symbol: {is: $tokenSymbol}}}}) {
                  Trade {
                    Currency {
                      Symbol
                    }
                    PriceInSOL
                  }
                }
              }
            }
            """
        )
        try:
            variables = {"tokenSymbol": token_symbol}
            result = await self.client.execute_async(query, variable_values=variables)
            trades = result.get('Solana', {}).get('DEXTrades', [])
            for trade in trades:
                if trade['Trade']['Currency']['Symbol'] == token_symbol:
                    logger.info(f"Найдена цена для {token_symbol}: {trade['Trade']['PriceInSOL']} SOL")
                    return trade['Trade']['PriceInSOL']
            logger.warning(f"Цена для {token_symbol} не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении цены для {token_symbol}: {e}")
            return None

    async def get_transaction_type(self, transaction_hash: str) -> str:
        query = gql(
            """
            query MyQuery($transactionHash: String!) {
              Solana {
                DEXTrades(where: {Transaction: {Hash: {is: $transactionHash}}}) {
                  Trade {
                    Side
                  }
                }
              }
            }
            """
        )
        try:
            variables = {"transactionHash": transaction_hash}
            result = await self.client.execute_async(query, variable_values=variables)
            trades = result.get('Solana', {}).get('DEXTrades', [])
            for trade in trades:
                side = trade['Trade']['Side']
                if side == "BUY":
                    logger.info(f"Транзакция {transaction_hash} определена как покупка")
                    return "buy"
                elif side == "SELL":
                    logger.info(f"Транзакция {transaction_hash} определена как продажа")
                    return "sell"
            logger.warning(f"Транзакция {transaction_hash} не является торговлей, определена как перевод")
            return "transfer"  # По умолчанию, если это не торговля
        except Exception as e:
            logger.error(f"Ошибка при определении типа транзакции {transaction_hash}: {e}")
            return "transfer"

    async def get_token_details(self, transaction_hash: str) -> tuple[Optional[str], Optional[float], Optional[float]]:
        # Проверяем, является ли транзакция торговлей (DEXTrade)
        dex_trade_query = gql(
            """
            query MyQuery($transactionHash: String!) {
              Solana {
                DEXTrades(where: {Transaction: {Hash: {is: $transactionHash}}}) {
                  Trade {
                    Side
                    BaseAmount
                    QuoteAmount
                    Currency {
                      Address
                      Symbol
                    }
                    QuoteCurrency {
                      Address
                      Symbol
                    }
                  }
                }
              }
            }
            """
        )
        try:
            variables = {"transactionHash": transaction_hash}
            result = await self.client.execute_async(dex_trade_query, variable_values=variables)
            trades = result.get('Solana', {}).get('DEXTrades', [])
            for trade in trades:
                token_address = trade['Trade']['Currency']['Address']  # Адрес базового токена
                base_amount = trade['Trade']['BaseAmount']  # Количество базового токена (купленного/проданного)
                quote_amount = trade['Trade']['QuoteAmount']  # Количество котируемого токена (например, SOL)
                side = trade['Trade']['Side']
                logger.info(f"Торговая операция {transaction_hash}: {side}, базовый токен {token_address} ({trade['Trade']['Currency']['Symbol']}), количество {base_amount}, котируемый токен {trade['Trade']['QuoteCurrency']['Symbol']}, количество {quote_amount}")
                return token_address, base_amount, quote_amount
        except Exception as e:
            logger.warning(f"Данные о торговой операции для {transaction_hash} не найдены в DEXTrades: {e}")

        # Если это не торговая операция, проверяем, является ли это переводом токена (Transfer)
        transfer_query = gql(
            """
            query MyQuery($transactionHash: String!) {
              Solana {
                Transfers(where: {Transaction: {Hash: {is: $transactionHash}}}) {
                  Transfer {
                    Amount
                    Currency {
                      Address
                      Symbol
                    }
                  }
                }
              }
            }
            """
        )
        try:
            result = await self.client.execute_async(transfer_query, variable_values=variables)
            transfers = result.get('Solana', {}).get('Transfers', [])
            for transfer in transfers:
                token_address = transfer['Transfer']['Currency']['Address']
                amount = transfer['Transfer']['Amount']
                logger.info(f"Перевод {transaction_hash}: токен {token_address} ({transfer['Transfer']['Currency']['Symbol']}), количество {amount}")
                return token_address, amount, None  # Для переводов возвращаем только количество и None для quote_amount
            logger.warning(f"Данные о переводе для {transaction_hash} не найдены в Transfers")
            return None, None, None
        except Exception as e:
            logger.error(f"Ошибка при получении данных о токене для {transaction_hash}: {e}")
            return None, None, None

    async def close(self):
        """
        Закрывает соединение с Bitquery.
        """
        try:
            await self.transport.close()
            logger.info("Соединение с Bitquery успешно закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с Bitquery: {e}")