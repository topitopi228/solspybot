import aiohttp
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
import os
import asyncio
import base64
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логгера
logger = logging.getLogger(__name__)


class HeliusApi:
    def __init__(self, api_token: str = None, rpc_endpoint: str = "https://mainnet.helius-rpc.com"):
        # Получаем API-ключ из переменной окружения, если не передан явно
        self.api_token = api_token or os.getenv("HELIUS_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "HELIUS_API_TOKEN не найден. Укажи его в .env как HELIUS_API_TOKEN=ваш_токен или передай в конструкторе.")

        # Проверяем формат токена
        self.api_token = self.api_token.strip()
        if not self.api_token:
            raise ValueError("API токен Helius пуст или некорректен.")

        logger.info(f"Инициализация Helius API с токеном: {self.api_token[:5]}... (сокрыт для безопасности)")

        # Формируем URL для JSON-RPC
        self.rpc_url = f"{rpc_endpoint}?api-key={self.api_token}"

        # Настраиваем заголовки
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }

    async def _make_rpc_request(self, method: str, params: List[Any]) -> Dict[str, Any]:
        """Универсальный метод для отправки JSON-RPC запросов без сессии."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        logger.debug(f"Запрос к Helius RPC: {self.rpc_url} с телом: {payload}")

        try:
            await asyncio.sleep(1)  # Задержка для предотвращения превышения лимита
            async with aiohttp.request(
                    "POST",
                    self.rpc_url,
                    json=payload,
                    headers=self.headers,
                    ssl=False
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    logger.error(f"Ошибка Helius RPC: {response.status} - {response_text}")
                    return {}

                data = await response.json()
                logger.debug(f"Ответ от Helius RPC: {data}")
                if "error" in data:
                    logger.error(f"Ошибка в RPC-запросе: {data['error']}")
                    return {}

                return data.get("result", {})

        except Exception as e:
            logger.error(f"Ошибка выполнения RPC-запроса: {str(e)}")
            return {}

    async def get_token_balance(self, wallet_address: str, mint_address: str) -> Dict[str, Any]:
        """
        Возвращает информацию о балансе конкретного токена на кошельке через JSON-RPC.
        """
        try:
            wallet_pubkey = Pubkey.from_string(wallet_address)
            mint_pubkey = Pubkey.from_string(mint_address)
            token_account_address = Pubkey.find_program_address(
                seeds=[
                    wallet_pubkey.__bytes__(),
                    TOKEN_PROGRAM_ID.__bytes__(),
                    mint_pubkey.__bytes__()
                ],
                program_id=ASSOCIATED_TOKEN_PROGRAM_ID
            )[0]
            logger.info(
                f"Вычисленный ATA для кошелька {wallet_address} и токена {mint_address}: {token_account_address}")

            # Добавляем задержку для синхронизации
            logger.info("Ожидание синхронизации данных (5 секунд)...")
            await asyncio.sleep(3)

            params = [str(token_account_address), {"commitment": "finalized"}]
            result = await self._make_rpc_request("getTokenAccountBalance", params)
            logger.info(f"Balance result для {token_account_address}: {result}")

            if not result or "value" not in result:
                logger.info(f"Токен-аккаунт для {mint_address} не найден на кошельке {wallet_address}. Баланс: 0")
                metadata = await self.get_token_metadata(mint_address)
                return {
                    "mint_address": mint_address,
                    "symbol": metadata.get("symbol", "Unknown"),
                    "name": metadata.get("name", "Unknown"),
                    "balance": 0.0
                }

            value = result["value"]
            logger.info(
                f"Полные данные баланса: amount={value.get('amount')}, decimals={value.get('decimals')}, uiAmount={value.get('uiAmount')}")

            metadata = await self.get_token_metadata(mint_address)
            token_decimals = metadata.get("decimals", 6)  # Используем decimals из метаданных
            logger.info(f"Decimals из метаданных: {token_decimals}")

            raw_amount = int(value.get("amount", 0))
            calculated_ui_amount = raw_amount / (10 ** token_decimals) if raw_amount > 0 else 0.0
            logger.info(f"Рассчитанный uiAmount: {calculated_ui_amount}")

            token_amount = calculated_ui_amount  # Используем рассчитанное значение

            token_data = {
                "mint_address": mint_address,
                "symbol": metadata.get("symbol", "Unknown"),
                "name": metadata.get("name", "Unknown"),
                "balance": token_amount,
                "raw_amount": raw_amount,
                "decimals": token_decimals
            }
            logger.info(f"Найден токен {mint_address} на кошельке {wallet_address}: {token_data}")
            return token_data

        except Exception as e:
            logger.error(f"Ошибка получения данных о токене {mint_address} для кошелька {wallet_address}: {str(e)}")
            return {}

    async def get_token_metadata(self, mint_address: str) -> Dict[str, Any]:
        try:
            # Вычисляем адрес Metaplex Metadata PDA с использованием solders
            metadata_program_id = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
            mint_pubkey = Pubkey.from_string(mint_address)
            seeds = [
                b"metadata",
                metadata_program_id.__bytes__(),
                mint_pubkey.__bytes__()
            ]
            metadata_pda, _ = Pubkey.find_program_address(seeds, metadata_program_id)

            # Запрашиваем данные Metaplex Metadata
            params = [
                str(metadata_pda),
                {"encoding": "base64", "commitment": "finalized"}
            ]
            result = await self._make_rpc_request("getAccountInfo", params)

            if not result or "value" not in result:
                logger.error(f"Не удалось получить Metaplex метаданные для {mint_address}")
                return {"symbol": "Unknown", "name": "Unknown"}

            # Декодируем данные
            account_data = result.get("value", {}).get("data", [])
            if not account_data or len(account_data) < 1:
                logger.error(f"Metaplex метаданные для {mint_address} пусты")
                return {"symbol": "Unknown", "name": "Unknown"}

            decoded_data = base64.b64decode(account_data[0])
            logger.info(f"Декодированные данные: {decoded_data}")

            # Извлекаем name (начинается с 65-го байта)
            name_start = 65
            # Ищем первый непустой байт (не 0x00 или 0x20)
            name_data_start = name_start
            while name_data_start < len(decoded_data) and decoded_data[name_data_start] in (0x00, 0x20):
                name_data_start += 1
            name_end = name_data_start + decoded_data[name_data_start:].index(b'\x00') if b'\x00' in decoded_data[
                                                                                                     name_data_start:] else name_data_start + 32
            logger.info(f"Name data start: {name_data_start}, Name end: {name_end}")
            name_raw = decoded_data[name_data_start:name_end]
            logger.info(f"Raw name bytes: {name_raw}")
            try:
                name = name_raw.decode("utf-8").strip("\x00")
            except UnicodeDecodeError:
                name = name_raw.decode("utf-8", errors="replace").strip("\x00")

            # Извлекаем symbol (начинается с 101-го байта)
            symbol_start = name_start + 32 + 4  # Пропускаем name и 4 байта для длины symbol
            # Ищем первый непустой байт (не 0x00 или 0x0a)
            symbol_data_start = symbol_start
            while symbol_data_start < len(decoded_data) and decoded_data[symbol_data_start] in (0x00, 0x0a):
                symbol_data_start += 1
            symbol_end = symbol_data_start + decoded_data[symbol_data_start:].index(b'\x00') if b'\x00' in decoded_data[
                                                                                                           symbol_data_start:] else symbol_data_start + 32
            logger.info(f"Symbol data start: {symbol_data_start}, Symbol end: {symbol_end}")
            symbol_raw = decoded_data[symbol_data_start:symbol_end]
            logger.info(f"Raw symbol bytes: {symbol_raw}")
            try:
                symbol = symbol_raw.decode("utf-8").strip("\x00")
            except UnicodeDecodeError:
                symbol = symbol_raw.decode("utf-8", errors="replace").strip("\x00")

            mint_account_info = await self._make_rpc_request("getAccountInfo", [mint_address, {"encoding": "base64",
                                                                                               "commitment": "confirmed"}])
            if mint_account_info and "value" in mint_account_info and mint_account_info["value"]:
                mint_data = base64.b64decode(mint_account_info["value"]["data"][0])
                decimals = int(mint_data[44]) if len(mint_data) > 44 else 6  # Позиция decimals в данных SPL-токена
                logger.info(f"Decimals токена {mint_address}: {decimals}")
            else:
                decimals = 6  # Значение по умолчанию
                logger.warning(
                    f"Не удалось получить decimals для {mint_address}, использовано значение по умолчанию: 6")

            return {
                "symbol": symbol if symbol else "Unknown",
                "name": name if name else "Unknown",
                "decimals": decimals
            }

        except Exception as e:
            logger.error(f"Ошибка получения метаданных для {mint_address}: {str(e)}")
        return {"symbol": "Unknown", "name": "Unknown", "decimals": 6}
