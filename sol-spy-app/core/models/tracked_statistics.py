from datetime import datetime
from sqlalchemy import  Integer, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import  Mapped, mapped_column
from sqlalchemy.sql import func
from core.models.base import Base
from typing import Optional





class TrackedStatistics(Base):
    __tablename__ = "tracked_statistics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    tracked_wallet_id: Mapped[int] = mapped_column(ForeignKey("tracked_wallets.id"), nullable=False)  # Унікальний зовнішній ключ
    deal_count: Mapped[int] = mapped_column(Integer, nullable=False)  # Кількість угод
    earned_sol: Mapped[float] = mapped_column(Float, nullable=False)  # Зароблені SOL (може бути плюсове або мінусове)
    average_weekly_deals: Mapped[float] = mapped_column(Float, nullable=False)  # Середня кількість угод за тиждень
    net_sol_increase: Mapped[float] = mapped_column(Float, nullable=False)  # Чистий приріст SOL від угод
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, server_default=func.now())  # Дата створення запису








