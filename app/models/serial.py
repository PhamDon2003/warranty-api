from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.dealer import Dealer
    from app.models.customer import Customer


class Serial(Base):
    __tablename__ = "serials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial_no: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    dealer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dealers.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="in_stock", nullable=False)  # in_stock | shipped | activated
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    activated_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="serials")
    dealer: Mapped[Optional["Dealer"]] = relationship("Dealer", back_populates="serials")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="serials")

