from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from core.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.sql import func
from enum import Enum as PyEnum


class Status(PyEnum):
    WAITING = 'waiting'
    BOUGHT = 'bought'
    FAILED = 'failed'


class SniperTarget(Base):
    __tablename__ = "sniper_targets"


    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # Адрес токена
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Название токена
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # Символ токена
    liquidity_threshold: Mapped[float] = mapped_column(Float, nullable=False)  # Минимальная ликвидность
    max_buy_amount: Mapped[float] = mapped_column(Float, nullable=False)  # Максимальная сумма для покупки
    status: Mapped[Status] = mapped_column(Enum(Status), default="waiting")  # Статус токена (waiting, bought, failed)
    created_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=func.now())  # Дата добавления
    last_checked_at: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=func.now())  # Последняя проверка


