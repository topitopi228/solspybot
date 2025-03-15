from datetime import datetime

from sqlalchemy import Column, Integer, String, TIMESTAMP, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from core.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from core.models.wallet_transaction import WalletTransaction
    from core.models.wallet_token import WalletToken

class WalletStatus(PyEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class FollowMode(PyEnum):
    ALL = 'all'
    BUY = 'buy'
    SELL = 'sell'


class TrackedWallet(Base):
    __tablename__ = "tracked_wallets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[WalletStatus] = mapped_column(Enum(WalletStatus), nullable=False)
    follow_mode:Mapped[FollowMode] = mapped_column(Enum(FollowMode), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())  # Дата добавления кошелька
    last_activity_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP, nullable=True)  # Дата последней активности кошелька
    sol_balance: Mapped[float] = mapped_column(Float, nullable=False)  # Текущее количество SOL на кошельке

    transactions: Mapped[list["WalletTransaction"]] = relationship("WalletTransaction", back_populates="tracked_wallet")