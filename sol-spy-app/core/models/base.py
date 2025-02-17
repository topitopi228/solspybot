from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from core.config import settings
from sqlalchemy import MetaData


class Base(DeclarativeBase):
    __abstract__ = True

    metadata = MetaData()
