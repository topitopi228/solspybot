from datetime import datetime

from sqlalchemy import  String, TIMESTAMP, Enum, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.models.wallet_transaction import WalletTransaction
    from core.models.bot_wallet import BotWallet



class FollowMode(PyEnum):
    COPY = 'copy'
    MONITOR ='monitor'

class CopyMode(PyEnum):
    COPY_PERCENT = 'copy_percent'
    COPY_XPERCENT = 'copy_xpercent'
    COPY_FIX = 'copy_fix'


class TrackedWallet(Base):
    __tablename__ = "tracked_wallets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    bot_wallet_id: Mapped[int] = mapped_column(ForeignKey("bot_wallets.id"), nullable=False)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False)
    follow_mode:Mapped[Optional[FollowMode]] = mapped_column(Enum(FollowMode), nullable=True)
    copy_mode: Mapped[Optional[CopyMode]] = mapped_column(Enum(CopyMode), nullable=True)
    is_tracking:Mapped[bool] =mapped_column(Boolean,default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())
    last_activity_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP, nullable=True)
    sol_balance: Mapped[float] = mapped_column(Float, nullable=False)

    transactions: Mapped[list["WalletTransaction"]] = relationship("WalletTransaction", back_populates="tracked_wallet")

    bot_wallet: Mapped["BotWallet"] = relationship("BotWallet", back_populates="tracked_wallets")

