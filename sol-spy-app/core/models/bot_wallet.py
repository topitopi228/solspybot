from sqlalchemy import Column, Integer, String, TIMESTAMP, Numeric, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.models.my_wallet_transaction import MyWalletTransaction


class BotWallet(Base):
    __tablename__ = "bot_wallets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String, nullable=False)
    private_key: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[float] = mapped_column(Numeric, nullable=True)
    last_updated_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP, nullable=True)


    transactions: Mapped[list["MyWalletTransaction"]] = relationship("MyWalletTransaction", back_populates="bot_wallet")
