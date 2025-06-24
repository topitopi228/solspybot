import aiohttp
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import os
import asyncio
import base64
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

load_dotenv()
logger = logging.getLogger(__name__)


class HeliusApi:
    def __init__(self, api_token: str = None, rpc_endpoint: str = "https://mainnet.helius-rpc.com"):
        self.api_token = api_token or os.getenv("HELIUS_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "HELIUS_API_TOKEN не найден. Укажи его в .env как HELIUS_API_TOKEN=ваш_токен или передай в конструкторе.")

        self.api_token = self.api_token.strip()
        if not self.api_token:
            raise ValueError("API токен Helius пуст или некорректен.")

        logger.info(f"Инициализация Helius API с токеном: {self.api_token[:5]}... (сокрыт для безопасности)")

        self.rpc_url = f"{rpc_endpoint}?api-key={self.api_token}"
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Connection": "keep-alive"
        }

    async def _make_rpc_request(self, method: str, params: List[Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        logger.debug(f"Запрос к Helius RPC: {self.rpc_url} с телом: {payload}")

        try:
            await asyncio.sleep(1)
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
            logger.error(f"Ошибка выполнения RPC-запроса: {str(e)}", exc_info=True)
            return {}

    async def get_token_balance(self, wallet_address: str, mint_address: str) -> Dict[str, Any]:
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

            logger.info("Ожидание синхронизации данных (3 секунд)...")
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
            token_decimals = metadata.get("decimals", 6)
            logger.info(f"Decimals из метаданных: {token_decimals}")

            raw_amount = int(value.get("amount", 0))
            calculated_ui_amount = raw_amount / (10 ** token_decimals) if raw_amount > 0 else 0.0
            logger.info(f"Рассчитанный uiAmount: {calculated_ui_amount}")

            token_amount = calculated_ui_amount

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
            logger.error(f"Ошибка получения данных о токене {mint_address} для кошелька {wallet_address}: {str(e)}",
                         exc_info=True)
            return {}

    async def get_token_metadata(self, mint_address: str) -> Dict[str, Any]:
        try:
            metadata_program_id = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
            mint_pubkey = Pubkey.from_string(mint_address)
            seeds = [
                b"metadata",
                metadata_program_id.__bytes__(),
                mint_pubkey.__bytes__()
            ]
            metadata_pda, _ = Pubkey.find_program_address(seeds, metadata_program_id)

            params = [
                str(metadata_pda),
                {"encoding": "base64", "commitment": "finalized"}
            ]
            result = await self._make_rpc_request("getAccountInfo", params)

            if not result or "value" not in result:
                logger.error(f"Не удалось получить Metaplex метаданные для {mint_address}")
                return {"symbol": "Unknown", "name": "Unknown", "decimals": 6}

            account_data = result.get("value", {}).get("data", [])
            if not account_data or len(account_data) < 1:
                logger.error(f"Metaplex метаданные для {mint_address} пусты")
                return {"symbol": "Unknown", "name": "Unknown", "decimals": 6}

            decoded_data = base64.b64decode(account_data[0])
            logger.info(f"Декодированные данные: {decoded_data}")

            name_start = 65
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

            symbol_start = name_start + 32 + 4
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
                decimals = int(mint_data[44]) if len(mint_data) > 44 else 6
                logger.info(f"Decimals токена {mint_address}: {decimals}")
            else:
                decimals = 6
                logger.warning(
                    f"Не удалось получить decimals для {mint_address}, использовано значение по умолчанию: 6")

            return {
                "symbol": symbol if symbol else "Unknown",
                "name": name if name else "Unknown",
                "decimals": decimals
            }

        except Exception as e:
            logger.error(f"Ошибка получения метаданных для {mint_address}: {str(e)}", exc_info=True)
            return {"symbol": "Unknown", "name": "Unknown", "decimals": 6}

    async def get_transaction_info(self, transaction_hash: str) -> Dict:
        # Initialize transaction info
        transaction_info = {
            "transaction_type": "TRANSFER",
            "token_address": "",
            "token_symbol": "Unknown",
            "buy_amount": 0.0,
            "sell_amount": 0.0,
            "transfer_amount": 0.0,
            "dex_name": "",
            "transaction_hash": transaction_hash,
        }

        # DEX program IDs
        raydium_amm_program_id = "675kPX9MHTjS2zt1DYMimMnD2Dqi37ZnmcYrwjG3s2W"
        raydium_clmm_program_id = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
        jupiter_program_id = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
        pump_fun_program_id = "6EF8rrecthR5DkcocFusWxYxuUULjohJoXcBrL1t9tA"
        pump_fun_alt_program_id = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
        axiom_traiding_platform ="AxiomfHaWDemCFBLBayqnEnNwE6b7B2Qz3UmzMpgbMG6"
        meteora_dlmm_program_id = "J9G2mzdy3vrgY25GQA1pbysvNNtbnM4mQB2jH4tWT3Mx"
        solana_mint = "So11111111111111111111111111111111111111112"
        token_program_id = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

        try:
            # Request transaction details from Helius API
            params = [transaction_hash,
                      {"encoding": "jsonParsed", "commitment": "finalized", "maxSupportedTransactionVersion": 0}]
            result = await self._make_rpc_request("getTransaction", params)

            if not result or "meta" not in result or "transaction" not in result:
                logger.info(f"Transaction {transaction_hash} not found or invalid in Helius")
                return transaction_info

            meta = result["meta"]
            transaction = result["transaction"]
            message = transaction["message"]
            instructions = message.get("instructions", [])
            inner_instructions = meta.get("innerInstructions", [])
            account_keys = message.get("accountKeys", [])

            # Identify signer
            signer = account_keys[0]["pubkey"] if account_keys and isinstance(account_keys[0], dict) else None
            if not signer:
                logger.info(f"Transaction {transaction_hash} has no valid signer")
                return transaction_info

            # Detect DEX involvement
            dex_names = []
            for instruction in instructions + [inst for inner in inner_instructions for inst in
                                               inner.get("instructions", [])]:
                program_id = instruction.get("programId", "")
                logger.debug(f"Instruction programId: {program_id}")
                if program_id in (raydium_amm_program_id, raydium_clmm_program_id):
                    if "Raydium" not in dex_names: dex_names.append("Raydium")
                elif program_id == jupiter_program_id:
                    if "Jupiter" not in dex_names: dex_names.append("Jupiter")
                elif program_id in (pump_fun_program_id, pump_fun_alt_program_id):
                    if "Pump.fun AMM" not in dex_names: dex_names.append("Pump.fun AMM")
                elif program_id == meteora_dlmm_program_id:
                    if "Meteora DLMM" not in dex_names: dex_names.append("Meteora DLMM")
            is_trade = bool(dex_names)
            print(is_trade)
            dex_name = dex_names[0] if dex_names else ""
            logger.debug(f"Detected DEX: {dex_names}, is_trade: {is_trade}")

            # Find all accounts owned by the signer
            signer_accounts = {signer}
            for bal in meta.get("preTokenBalances", []) + meta.get("postTokenBalances", []):
                if bal["owner"] == signer:
                    signer_accounts.add(account_keys[bal["accountIndex"]]["pubkey"])
            logger.debug(f"Signer accounts: {signer_accounts}")

            # Track what the signer sends and receives (raw flows)
            tokens_sent = {}  # mint: amount
            tokens_received = {}  # mint: amount


            signer_index = 0  # Signer is typically the first account
            pre_balance = meta.get("preBalances", [0])[signer_index] / 1e9  # Convert lamports to SOL
            post_balance = meta.get("postBalances", [0])[signer_index] / 1e9  # Convert lamports to SOL
            fee = meta.get("fee", 0) / 1e9  # Transaction fee in SOL
            net_balance_change = post_balance - pre_balance- fee
            print(net_balance_change)
            logger.debug(
                f"pre_balance: {pre_balance}, post_balance: {post_balance}, fee: {fee}, net_balance_change: {net_balance_change}")

            for inner in inner_instructions:
                logger.debug(f"Inner instruction set: {inner}")
                for instruction in inner.get("instructions", []):
                    logger.debug(f"Instruction: {instruction}")
                    if instruction.get("programId") != token_program_id:
                        continue
                    parsed = instruction.get("parsed", {})
                    if parsed.get("type") not in ("transfer", "transferChecked"):
                        continue

                    info = parsed.get("info", {})
                    authority = info.get("authority", "")
                    source = info.get("source", "")
                    destination = info.get("destination", "")
                    amount = float(info.get("tokenAmount", {}).get("uiAmount", 0))
                    mint = info.get("mint", "")

                    # Skip if mint is invalid
                    if not mint or len(mint) != 44:  # Solana public keys are 44 characters in base58
                        logger.debug(f"Skipping invalid mint: {mint}")
                        continue

                    # Non-SOL token transfers
                    if source in signer_accounts or authority in signer_accounts:
                        tokens_sent[mint] = tokens_sent.get(mint, 0) + amount
                        logger.debug(f"Token sent: {amount} {mint} from {source}")
                    if destination in signer_accounts:
                        tokens_received[mint] = tokens_received.get(mint, 0) + amount
                        logger.debug(f"Token received: {amount} {mint} to {destination}")

            logger.debug(f"tokens_sent: {tokens_sent}, tokens_received: {tokens_received}")

            # Classify the transaction based on flows
            if is_trade:
                logger.debug(
                    f"Classifying trade: net_balance_change={net_balance_change}, tokens_received={tokens_received}, tokens_sent={tokens_sent}")
                if net_balance_change < 0 and tokens_received and not tokens_sent:
                    # BUY: Spent SOL, received tokens, didn't send tokens
                    mint, buy_amount = max(tokens_received.items(), key=lambda x: x[1])
                    transaction_info["transaction_type"] = "BUY"
                    transaction_info["token_address"] = mint
                    transaction_info["token_symbol"] = mint  # Use mint as symbol
                    transaction_info["buy_amount"] = buy_amount
                    transaction_info["sell_amount"] = abs(net_balance_change)  # Spent SOL
                    transaction_info["dex_name"] = dex_name
                    logger.info(f"Transaction {transaction_hash} classified as BUY "
                                f"(token: {mint}, amount: {buy_amount}, spent SOL: {abs(net_balance_change)})")
                elif net_balance_change > 0 and tokens_sent and not tokens_received:
                    # SELL: Received SOL, sent tokens, didn't receive tokens
                    mint, sell_amount = max(tokens_sent.items(), key=lambda x: x[1])
                    transaction_info["transaction_type"] = "SELL"
                    transaction_info["token_address"] = mint
                    transaction_info["token_symbol"] = mint  # Use mint as symbol
                    transaction_info["sell_amount"] = sell_amount
                    transaction_info["buy_amount"] = net_balance_change  # Received SOL
                    transaction_info["dex_name"] = dex_name
                    logger.info(f"Transaction {transaction_hash} classified as SELL "
                                f"(token: {mint}, amount: {sell_amount}, received SOL: {net_balance_change})")
                elif tokens_sent and tokens_received:
                    # SWAP: Sent tokens, received different tokens
                    sell_mint, sell_amount = max(tokens_sent.items(), key=lambda x: x[1])
                    buy_mint, buy_amount = max(tokens_received.items(), key=lambda x: x[1])
                    transaction_info["transaction_type"] = "SWAP"
                    transaction_info["token_address"] = f"{sell_mint}:{buy_mint}"
                    transaction_info["token_symbol"] = f"{sell_mint}:{buy_mint}"  # Use mints as symbol
                    transaction_info["sell_amount"] = sell_amount
                    transaction_info["buy_amount"] = buy_amount
                    transaction_info["dex_name"] = dex_name
                    logger.info(f"Transaction {transaction_hash} classified as SWAP "
                                f"(sold {sell_mint}: {sell_amount}, bought {buy_mint}: {buy_amount})")
            else:
                # Non-trade transaction
                if tokens_sent or tokens_received:
                    mint = max(tokens_sent, key=tokens_sent.get,
                               default=max(tokens_received, key=tokens_received.get, default=""))
                    amount = tokens_sent.get(mint, tokens_received.get(mint, 0))
                    transaction_info["transaction_type"] = "TRANSFER"
                    transaction_info["token_address"] = mint
                    transaction_info["token_symbol"] = mint
                    transaction_info["transfer_amount"] = amount
                    logger.info(f"Transaction {transaction_hash} classified as TRANSFER "
                                f"(token: {mint}, amount: {amount})")
                elif abs(net_balance_change) > 0:
                    transaction_info["transaction_type"] = "TRANSFER"
                    transaction_info["token_address"] = solana_mint
                    transaction_info["token_symbol"] = "SOL"
                    transaction_info["transfer_amount"] = abs(net_balance_change)
                    logger.info(f"Transaction {transaction_hash} classified as TRANSFER "
                                f"(token: SOL, amount: {abs(net_balance_change)})")

            return transaction_info

        except Exception as e:
            logger.error(f"Error fetching transaction info for {transaction_hash}: {str(e)}", exc_info=True)
            return transaction_info

    async def get_token_price_in_sol(self, token_address: str) -> Optional[float]:

        solana_mint = "So11111111111111111111111111111111111111112"  # Wrapped SOL (WSOL)
        raydium_amm_program_id = "675kPX9MHTjS2zt1DYMimMnD2Dqi37ZnmcYrwjG3s2W"  # Raydium AMM
        raydium_clmm_program_id = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"  # Raydium CLMM

        try:
            # Шаг 1: Получаем последние транзакции с токеном через Helius RPC
            params = [token_address, {
                "limit": 10,  # Ограничиваем количество транзакций для анализа
                "commitment": "finalized"
            }]
            signatures_result = await self._make_rpc_request("getSignaturesForAddress", params)

            if not signatures_result:
                logger.warning(f"No recent transactions found for token {token_address}")
                return None

            pool_address = None
            pool_type = None

            # Шаг 2: Анализируем транзакции, чтобы найти пул ликвидности
            for signature_info in signatures_result:
                tx_hash = signature_info.get("signature")
                if not tx_hash:
                    continue

                # Запрашиваем детали транзакции
                tx_params = [tx_hash, {
                    "encoding": "jsonParsed",
                    "commitment": "finalized",
                    "maxSupportedTransactionVersion": 0
                }]
                tx_result = await self._make_rpc_request("getTransaction", tx_params)

                if not tx_result:
                    continue

                # Извлекаем инструкции из транзакции
                message = tx_result.get("transaction", {}).get("message", {})
                instructions = message.get("instructions", [])
                account_keys = message.get("accountKeys", [])

                # Ищем инструкции, связанные с Raydium
                for instruction in instructions:
                    program_id = instruction.get("programId", "")
                    if program_id == raydium_amm_program_id:
                        pool_type = "AMM"
                    elif program_id == raydium_clmm_program_id:
                        pool_type = "CLMM"
                    else:
                        continue

                    # Ищем аккаунты, связанные с пулом
                    accounts_in_instruction = instruction.get("accounts", [])
                    print(f"Instruction accounts: {accounts_in_instruction}")  # Отладка

                    for account_ref in accounts_in_instruction:
                        # Проверяем, является ли account_ref индексом (int) или публичным ключом (str)
                        if isinstance(account_ref, int):
                            # Если это индекс, получаем аккаунт из account_keys
                            if account_ref < len(account_keys):
                                account = account_keys[account_ref]
                            else:
                                continue
                        elif isinstance(account_ref, str):
                            # Если это уже публичный ключ, используем его напрямую
                            account = account_ref
                        else:
                            continue

                        # Запрашиваем данные об аккаунте
                        account_info_params = [account, {
                            "encoding": "base64",
                            "commitment": "finalized"
                        }]
                        account_info = await self._make_rpc_request("getAccountInfo", account_info_params)

                        if not account_info or "value" not in account_info:
                            continue

                        account_data = account_info.get("value", {}).get("data", [])
                        if not account_data:
                            continue

                        # Проверяем, принадлежит ли аккаунт Raydium
                        owner = account_info.get("value", {}).get("owner", "")
                        if owner not in (raydium_amm_program_id, raydium_clmm_program_id):
                            continue

                        # Проверяем, содержит ли аккаунт данные о токене и SOL
                        decoded_data = base64.b64decode(account_data[0])
                        if len(decoded_data) < 264:  # Проверяем длину данных
                            continue

                        # Проверяем, есть ли в данных ссылки на наш токен и SOL
                        token_mint = str(Pubkey(decoded_data[32:64]))
                        sol_mint = str(Pubkey(decoded_data[64:96]))
                        if (token_mint == token_address and sol_mint == solana_mint) or \
                                (sol_mint == token_address and token_mint == solana_mint):
                            pool_address = account
                            break

                    if pool_address:
                        break

                if pool_address:
                    break

            if not pool_address:
                logger.warning(f"No liquidity pool found for token {token_address} using Helius API")
                return None

            logger.info(f"Found {pool_type} liquidity pool for token {token_address}: {pool_address}")

            # Шаг 3: Запрашиваем данные о пуле через Helius RPC
            params = [pool_address, {
                "encoding": "base64",
                "commitment": "finalized",
                "maxSupportedTransactionVersion": 0
            }]
            result = await self._make_rpc_request("getAccountInfo", params)

            if not result or "value" not in result:
                logger.error(f"Не удалось получить данные пула для {token_address}")
                return None

            account_data = result.get("value", {}).get("data", [])
            if not account_data or len(account_data) < 1:
                logger.error(f"Данные пула для {token_address} пусты")
                return None

            # Шаг 4: Декодируем данные пула
            decoded_data = base64.b64decode(account_data[0])

            # Шаг 5: Извлекаем баланс SOL и токена
            if pool_type == "AMM":
                # Для AMM пулов
                sol_balance = int.from_bytes(decoded_data[100:108], byteorder="little") / 10 ** 9  # SOL (9 decimals)
                token_balance = int.from_bytes(decoded_data[108:116], byteorder="little")
            else:  # CLMM
                # Для CLMM пулов
                sol_balance = int.from_bytes(decoded_data[248:256], byteorder="little") / 10 ** 9  # vaultA (SOL)
                token_balance = int.from_bytes(decoded_data[256:264], byteorder="little")  # vaultB (токен)

            # Шаг 6: Получаем decimals токена
            metadata = await self.get_token_metadata(token_address)
            token_decimals = metadata.get("decimals", 6)
            token_balance = token_balance / 10 ** token_decimals

            if token_balance == 0:
                logger.warning(f"Token balance in pool is 0 for {token_address}")
                return None

            # Шаг 7: Рассчитываем цену
            price_in_sol = sol_balance / token_balance
            logger.info(f"Found price for token {token_address}: {price_in_sol:.8f} SOL")
            return price_in_sol

        except Exception as e:
            logger.error(f"Error getting price for token {token_address}: {str(e)}", exc_info=True)
            return None
