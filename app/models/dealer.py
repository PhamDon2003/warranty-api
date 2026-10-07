from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.serial import Serial


class Dealer(Base):
    __tablename__ = "dealers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    users: Mapped[List["User"]] = relationship("User", back_populates="dealer")
    serials: Mapped[List["Serial"]] = relationship("Serial", back_populates="dealer")

