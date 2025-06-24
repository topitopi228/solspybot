from sqlalchemy import ForeignKey, String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.base import Base
from typing import Optional
from typing import TYPE_CHECKING, Optional


class WalletToken(Base):
    __tablename__ = "wallet_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True,autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("tracked_wallets.id", ondelete='CASCADE'), nullable=False)  # Связь с кошельком
    token_address: Mapped[str] = mapped_column(String, nullable=False)
    token_symbol: Mapped[str] = mapped_column(String, nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
