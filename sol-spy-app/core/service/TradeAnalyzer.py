
from core.db_helper import db_helper
from core.models.wallet_transaction import WalletTransaction
import logging
from typing import Dict, List
from sqlalchemy import select
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TradeAnalyzer:
    def __init__(self,session_factory):
        self.trades = {}
        self.session_factory = session_factory

    def analyze_trade(self, transaction: Dict) -> Dict:
        """
        Анализирует сделку, используя цену из данных транзакции, и возвращает результат.
        """
        wallet_address = transaction["wallet_address"]
        token_address = transaction["token_address"]
        transaction_type = transaction["transaction_action"]
        amount = transaction["buy_amount"] if transaction_type == "buy" else transaction["sell_amount"]
        price = transaction["price"]

        result = {
            "transaction_hash": transaction["transaction_hash"],
            "transaction_action": transaction_type,
            "token_symbol": transaction["token_symbol"],
            "amount": amount,
            "price": price,
            "status": None,
            "profit": None,
            "message": None
        }

        if not price:
            logger.error(f"Цена отсутствует для транзакции {transaction['transaction_hash']}")
            result["message"] = f"Цена отсутствует для транзакции {transaction['transaction_hash']}"
            return result

        if transaction_type == "buy":
            # Сохраняем данные о покупке
            if wallet_address not in self.trades:
                self.trades[wallet_address] = {}
            self.trades[wallet_address][token_address] = {
                "buy_price": price,
                "buy_amount": amount
            }
            result["message"] = f"Покупка: {amount} {transaction['token_symbol']} по цене {price:.8f} SOL"

        elif transaction_type == "sell":
            # Проверяем, есть ли данные о покупке
            if (wallet_address in self.trades and
                    token_address in self.trades[wallet_address]):
                buy_data = self.trades[wallet_address][token_address]
                buy_price = buy_data["buy_price"]
                buy_amount = buy_data["buy_amount"]

                # Рассчитываем прибыль/убыток
                sell_price = price
                profit_per_token = sell_price - buy_price
                total_profit = profit_per_token * min(buy_amount, amount)

                # Формируем результат
                status = "прибыль" if total_profit > 0 else "убыток"
                result["status"] = status
                result["profit"] = total_profit
                result["message"] = (f"Продажа: {amount} {transaction['token_symbol']} по цене {sell_price:.8f} SOL\n"
                                     f"Покупка была по {buy_price:.8f} SOL\n"
                                     f"Результат: {status} {total_profit:.4f} SOL")

                # Удаляем данные о покупке, если продали всё
                if amount >= buy_amount:
                    del self.trades[wallet_address][token_address]
            else:
                logger.warning(f"Нет данных о покупке для {token_address} от {wallet_address}")
                result["message"] = f"Нет данных о покупке для {token_address} от {wallet_address}"

        return result

    async def analyze_transactions_from_db(self, time_delta_minutes: int = 60) -> List[Dict]:
        """
        Извлекает транзакции из БД за последние time_delta_minutes минут и анализирует их.
        Возвращает список результатов анализа.
        """
        time_threshold = datetime.utcnow() - timedelta(minutes=time_delta_minutes)
        results = []

        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(WalletTransaction)
                .filter(WalletTransaction.timestamp >= time_threshold)
                .order_by(WalletTransaction.timestamp.asc())
            )
            transactions = result.scalars().all()

            for tx in transactions:
                transaction_data = {
                    "wallet_address": tx.wallet_address,
                    "transaction_hash": tx.transaction_hash,
                    "transaction_action": tx.transaction_action,
                    "token_address": tx.token_address,
                    "token_symbol": tx.token_symbol,
                    "buy_amount": tx.buy_amount,
                    "sell_amount": tx.sell_amount,  
                    "transfer_amount": tx.transfer_amount,
                    "dex_name": tx.dex_name,
                    "price": tx.price,
                    "timestamp": tx.timestamp.timestamp()
                }
                analysis_result = self.analyze_trade(transaction_data)
                results.append(analysis_result)

        return results
