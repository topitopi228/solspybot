from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from core.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class BotLog(Base):
    __tablename__ = "bot_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("tracked_wallets.id",ondelete='CASCADE'), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # "buy", "sell", "error" и т.д.
    details: Mapped[Text] = mapped_column(Text, nullable=True)  # Дополнительные детали
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, server_default=func.now())
