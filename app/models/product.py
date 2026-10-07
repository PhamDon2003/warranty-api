from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.serial import Serial


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("warranty_months > 0", name="check_warranty_months_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    warranty_months: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    serials: Mapped[List["Serial"]] = relationship("Serial", back_populates="product")

