
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional,  Dict

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import os
from dotenv import load_dotenv
import logging

from httpx import TransportError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv()


class BitqueryAPI:
    def __init__(self, endpoint: str = "https://streaming.bitquery.io/eap", api_token: str = None):
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


    async def get_token_price_in_sol(self, token_address: str) -> Optional[float]:
        # WSOL mint address
        sol_mint = "So11111111111111111111111111111111111111112"

        query = gql(
            """
            query GetTokenPriceInSOL($tokenAddress: String!, $solMint: String!) {
              Solana {
                DEXTradeByTokens(
                  where: {
                    Trade: {
                      Currency: {MintAddress: {is: $tokenAddress}},
                      Side: {Currency: {MintAddress: {is: $solMint}}}
                    }
                  }
                  orderBy: {descending: Block_Time}
                  limit: {count: 1}
                ) {
                  Trade {
                    Currency {
                      MintAddress
                      Symbol
                    }
                    Price
                  }
                }
              }
            }
            """
        )

        try:
            variables = {
                "tokenAddress": token_address,
                "solMint": sol_mint
            }

            result = await self.client.execute_async(query, variable_values=variables)
            trades = result.get('Solana', {}).get('DEXTradeByTokens', [])

            if trades and len(trades) > 0:
                trade = trades[0]['Trade']
                # Получаем цену как строку из ответа для точного представления
                price_str = str(trade.get('Price', 0))
                # Преобразуем в Decimal для точного расчета
                price_decimal = Decimal(price_str).quantize(Decimal('0.00000001'),
                                                            rounding=ROUND_HALF_UP)  # Округляем до 8 знаков после запятой
                # Конвертируем в float для возврата
                price_float = float(price_decimal)

                symbol = trade.get('Currency', {}).get('Symbol', 'Unknown')
                logger.info(f"Found price for token {symbol} ({token_address}): {price_float} SOL")

                # Форматируем цену с 8 десятичными знаками для отображения
                formatted_price_fixed = f"{price_float:.8f}"  # Показывает 8 десятичных знаков (например, 0.00002389)
                print(f"Token price (fixed decimal): {formatted_price_fixed} SOL")

                return price_float

            logger.warning(f"Price for token with address {token_address} not found")
            return None

        except Exception as e:
            logger.error(f"Error getting price for token with address {token_address}: {str(e)}")
            return None

    async def get_transaction_info(self, transaction_hash: str) -> Dict:
        query = gql(
            """
            query GetSolanaTransactionType($transactionHash: String!) {
              Solana {  # Исправлено на "solana" с маленькой буквы
                DEXTrades(
                  where: {Transaction: {Signature: {is: $transactionHash}}}
                  limit: {count: 1}
                ) {
                  Transaction {
                    Signature
                  }
                  Trade {
                    Buy {
                      Amount
                      Currency {
                        MintAddress
                        Symbol
                      }
                    }
                    Sell {
                      Amount
                      Currency {
                        MintAddress
                        Symbol
                      }
                    }
                    Dex {
                      ProtocolName
                      ProtocolFamily
                    }
                  }
                }
              }
            }
            """
        )

        transaction_info = {
            "transaction_type": "transfer",
            "token_address": "",
            "token_symbol": "Unknown",
            "buy_amount": 0.0,
            "sell_amount": 0.0,
            "transfer_amount": 0.0,
            "dex_name": ""
        }

        try:
            variables = {"transactionHash": transaction_hash}
            result = await self.client.execute_async(query, variable_values=variables)

            # Проверяем, является ли транзакция торговлей (DEXTrades)
            dex_trades = result.get('Solana', {}).get('DEXTrades', [])
            if dex_trades:
                trade = dex_trades[0]['Trade']

                # Определяем тип транзакции на основе токенов и сумм
                solana_mint = "So11111111111111111111111111111111111111112"  # WSOL mint address

                if (trade.get('Buy') and
                        trade.get('Sell') and trade['Sell'].get('Currency', {}).get('MintAddress') == solana_mint and
                        float(trade['Sell'].get('Amount', 0.0)) > 0):
                    transaction_info["transaction_type"] = "buy"
                    transaction_info["token_address"] = trade['Buy']['Currency'].get('MintAddress', "")
                    transaction_info["token_symbol"] = trade['Buy']['Currency'].get('Symbol', "Unknown")
                    transaction_info["buy_amount"] = float(trade['Buy'].get('Amount', 0.0))
                    transaction_info["sell_amount"] = float(trade['Sell'].get('Amount', 0.0))
                    transaction_info["dex_name"] = trade['Dex'].get('ProtocolFamily', "Unknown")
                    logger.info(
                        f"Transaction {transaction_hash} identified as a buy (sent SOL, received token: {transaction_info['token_symbol']}, amount: {transaction_info['buy_amount']}, SOL spent: {transaction_info['sell_amount']})")
                    return transaction_info
                # Если купили WSOL (SOL) и продали токен — это "sell" (отправил токен, получил SOL)
                elif (trade.get('Sell') and
                      trade.get('Buy') and trade['Buy'].get('Currency', {}).get('MintAddress') == solana_mint and
                      float(trade['Buy'].get('Amount', 0.0)) > 0):
                    transaction_info["transaction_type"] = "sell"
                    transaction_info["token_address"] = trade['Sell']['Currency'].get('MintAddress',
                                                                                      "")  # Токен, отправленный (Sell)
                    transaction_info["token_symbol"] = trade['Sell']['Currency'].get('Symbol',
                                                                                     "Unknown")  # Символ токена, отправленного
                    transaction_info["sell_amount"] = float(trade['Sell'].get('Amount', 0.0))
                    transaction_info["buy_amount"] = float(trade['Buy'].get('Amount', 0.0))
                    transaction_info["dex_name"] = trade['Dex'].get('ProtocolFamily', "Unknown")
                    logger.info(
                        f"Transaction {transaction_hash} identified as a sell (sent token: {transaction_info['token_symbol']}, amount: {transaction_info['buy_amount']}, received SOL: {transaction_info['sell_amount']})")
                    return transaction_info
            else:
                logger.info(f"Transaction {transaction_hash} identified as a transfer (no DEX trade found)")
                return transaction_info


        except (TransportError, KeyError, ValueError, Exception) as e:
            logger.error(f"Error getting transaction info for {transaction_hash}: {str(e)}")
            return {
                "transaction_type": "transfer",
                "token_address": "",
                "token_symbol": "Unknown",
                "buy_amount": 0.0,
                "sell_amount": 0.0,
                "transfer_amount": 0.0,
                "dex_name": ""
            }

    async def close(self):
        """
        Закрывает соединение с Bitquery.
        """
        try:
            await self.transport.close()
            logger.info("Соединение с Bitquery успешно закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения с Bitquery: {e}")
