from sqlalchemy import Column, Integer, String, TIMESTAMP, Numeric, ForeignKey, Float,Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column
from core.models.base import Base
from sqlalchemy.sql import func
from typing import TYPE_CHECKING

from enum import Enum as PyEnum


if TYPE_CHECKING:
    from core.models.bot_wallet import BotWallet



class TransactionStatus(PyEnum):
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'

class TransactionAction(PyEnum):
    BUY = 'buy'
    SELL = 'sell'
    TRANSFER = 'transfer'


class MyWalletTransaction(Base):
    __tablename__ = "my_wallet_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("bot_wallets.id", ondelete='CASCADE'), nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    transaction_action: Mapped[TransactionAction] = mapped_column(Enum(TransactionAction), nullable=False) # "buy" или "sell"
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False)
    token_address: Mapped[str] = mapped_column(String, nullable=False)
    token_symbol: Mapped[str] = mapped_column(String, nullable=False)
    base_amount: Mapped[float] = mapped_column(Float, nullable=False)
    quote_amount: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, server_default=func.now())

    bot_wallet: Mapped["BotWallet"] = relationship("BotWallet", back_populates="transactions")