from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select

from core.models.bot_wallet import BotWallet
from core.models.tracked_wallet import TrackedWallet
from core.models.tracked_statistics import TrackedStatistics
import logging
from core.models.wallet_transaction import WalletTransaction, TransactionAction

logger = logging.getLogger(__name__)


class TrackedStatisticsService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def count_deals(self, wallet: TrackedWallet):
        try:
            current_time = datetime.now(timezone.utc)
            one_hour_ago = current_time - timedelta(hours=1)
            async with self.session_factory() as session:
                transactions = (
                    session.query(WalletTransaction)
                    .filter(WalletTransaction.wallet_id == wallet.id)
                    .filter(WalletTransaction.timestamp >= one_hour_ago)
                    .all()
                )

                deal_count = sum(
                    1 for tx in transactions if tx.transaction_action == TransactionAction.BUY.value
                )
                return deal_count
        except Exception as e:
            session.rollback()
            raise Exception(f"Помилка при створенні статистики: {str(e)}")

    async def create_statistics_for_all_wallets(self):

        async with self.session_factory() as session:
            try:

                # Отримуємо всі tracked_wallets
                wallets = session.query(TrackedWallet).all()

                for wallet in wallets:
                    deal_count = await self.count_deals(wallet)

                    average_weekly_deals = deal_count * 7 * 24
                    net_sol_increase = 0

                    # Створюємо новий запис статистики для цього гаманця
                    new_stat = TrackedStatistics(
                        tracked_wallet_id=wallet.id,
                        deal_count=deal_count,
                        earned_sol=0,
                        average_weekly_deals=average_weekly_deals,
                        net_sol_increase=net_sol_increase
                    )
                    session.add(new_stat)

                session.commit()
            except Exception as e:
                session.rollback()
                raise Exception(f"Помилка при створенні статистики: {str(e)}")

    async def get_statistics_for_bot_wallet(self, user, wallet_address: str):
        async with self.session_factory() as session:
            try:
                # Отримання активного бот-гаманця для користувача
                bot_wallet = await session.execute(
                    select(BotWallet).filter(BotWallet.user_id == user.id, BotWallet.status == True)
                )
                bot_wallet = bot_wallet.scalar_one_or_none()
                if not bot_wallet:
                    logger.warning(f"No active bot wallet found for user {user.id}")
                    return []

                # Отримання відстежуваного гаманця за адресою
                tracked_wallet = await session.execute(
                    select(TrackedWallet).filter(
                        TrackedWallet.bot_wallet_id == bot_wallet.id,
                        TrackedWallet.wallet_address == wallet_address
                    )
                )
                tracked_wallet = tracked_wallet.scalars().first()  # Беремо перший збіг або None
                if not tracked_wallet:
                    logger.warning(
                        f"No tracked wallet found with address {wallet_address} for bot wallet {bot_wallet.id}")
                    return []

                # Отримання статистики для конкретного відстежуваного гаманця
                statistics = await session.execute(
                    select(TrackedStatistics).filter(
                        TrackedStatistics.tracked_wallet_id == tracked_wallet.id
                    )
                )
                statistics_list = statistics.scalars().all()

                logger.debug(f"Retrieved {len(statistics_list)} statistics entries for tracked wallet {wallet_address}")
                return statistics_list

            except Exception as e:
                logger.error(f"Помилка при витяганні статистики: {str(e)}", exc_info=True)
                raise Exception(f"Помилка при витяганні статистики: {str(e)}")
