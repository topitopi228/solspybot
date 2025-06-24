from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column,relationship
from sqlalchemy.sql import func
from core.models.base import Base
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.bot_wallet import BotWallet
    from core.models.auth_token import AuthToken

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # Зазвичай пароль хешується
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    bot_wallets: Mapped[list["BotWallet"]] = relationship("BotWallet", back_populates="user")

    tokens: Mapped[list["AuthToken"]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )