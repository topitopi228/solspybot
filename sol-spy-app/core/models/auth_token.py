from enum import unique
from typing import TYPE_CHECKING
from pydantic import BaseModel
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base

if TYPE_CHECKING:
    from core.models.user import User


class AuthToken(Base):
    __tablename__ = 'auth_tokens'
    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(unique=True,index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'))

    user: Mapped["User"] = relationship(
        back_populates="tokens",
        lazy="selectin",
    )