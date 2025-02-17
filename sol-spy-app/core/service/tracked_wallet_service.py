from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from core.models.tracked_wallet import TrackedWallet  # Импорт модели TrackedWallet
from api.solana_api import SolanaAPI  # Импорт класса SolanaAPI
from core.models.tracked_wallet import FollowMode, WalletStatus
from core.db_helper import db_helper


class WalletService:
    def __init__(self):
        self.solana_api = SolanaAPI()

    async def add_wallet_data(self, wallet_address: str, follow_mode: FollowMode):
        """
        Добавляет кошелёк в базу данных для отслеживания.
        """
        # Проверяем, существует ли уже кошелёк в базе
        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            existing_wallet = result.scalar_one_or_none()

        if existing_wallet:
            raise ValueError(f"Кошелёк {wallet_address} уже отслеживается.")

        # Получаем начальные данные о кошельке через Solana API
        try:
            balance = await self.solana_api.get_balance(wallet_address)
        except Exception as e:
            raise ValueError(f"Ошибка получения данных о балансе кошелька: {e}")

        # Создаём новую сущность TrackedWallet
        new_wallet = TrackedWallet(
            wallet_address=wallet_address,
            status=WalletStatus.ACTIVE,  # Устанавливаем статус "ACTIVE" по умолчанию
            follow_mode=follow_mode,  # Режим отслеживания передаётся как аргумент
            created_at=datetime.now(timezone.utc),
            last_activity_at=None,  # Пока нет активности
            sol_balance=balance  # Устанавливаем начальный баланс
        )
        async with db_helper.session_factory() as session:
        # Добавляем кошелёк в сессию
            try:
                session.add(new_wallet)
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError(f"Ошибка: Кошелёк {wallet_address} уже существует в базе.")

    async def update_wallet_data(self, wallet_address: str):
        """
        Обновляет данные кошелька в базе данных.
        """
        # Получаем данные о кошельке из Solana API
        balance = await self.solana_api.get_balance(wallet_address)
        transactions = await self.solana_api.get_wallet_transactions(wallet_address, limit=5)

        # Получаем кошелек из базы данных
        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            tracked_wallet = result.scalar_one_or_none()

            if tracked_wallet.status != WalletStatus.ACTIVE:
                print(f"Кошелёк {wallet_address} имеет статус {tracked_wallet.status}. Обновление данных пропущено.")
                return
            if tracked_wallet:
                # Обновляем данные в сущности
                tracked_wallet.sol_balance = balance
                tracked_wallet.last_activity_at = datetime.now(timezone.utc)  # Обновляем дату последней активности

                # Можно также добавить логику для обновления статуса или других полей
                # Например, проверка на наличие транзакций для изменения состояния кошелька
                if transactions:
                    # Если транзакции есть, можно обновить статус или выполнить другую логику
                    pass

                # Сохраняем изменения в базе данных
                await session.commit()

    async def update_wallet_status(self, wallet_address: str, new_status: WalletStatus):
        """
        Обновляет статус кошелька.
        """
        # Проверяем, существует ли кошелёк в базе данных
        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(TrackedWallet).filter(TrackedWallet.wallet_address == wallet_address))
            tracked_wallet = result.scalar_one_or_none()

            if not tracked_wallet:
                raise ValueError(f"Кошелёк {wallet_address} не найден в базе данных.")

            # Обновляем статус
            tracked_wallet.status = new_status

            # Сохраняем изменения в базе данных
            await session.commit()
        print(f"Статус кошелька {wallet_address} успешно обновлён на {new_status.name}.")

    async def close(self):
        """
        Закрывает соединение с клиентом.
        """
        await self.solana_api.close()
