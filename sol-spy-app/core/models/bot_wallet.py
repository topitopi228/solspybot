from email.policy import default

from sqlalchemy import Column, Integer, String, TIMESTAMP, Numeric, ForeignKey, Float, Boolean, false
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.models.my_wallet_transaction import MyWalletTransaction
    from core.models.user import User
    from core.models.tracked_wallet import TrackedWallet


class BotWallet(Base):
    __tablename__ = "bot_wallets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    token_address: Mapped[str] = mapped_column(String, nullable=False)
    private_key: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[float] = mapped_column(Numeric, nullable=True)
    last_updated_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP, nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=false)


    transactions: Mapped[list["MyWalletTransaction"]] = relationship("MyWalletTransaction", back_populates="bot_wallet")

    tracked_wallets: Mapped[list["TrackedWallet"]] = relationship("TrackedWallet", back_populates="bot_wallet")
    user: Mapped["User"] = relationship("User", back_populates="bot_wallets")
