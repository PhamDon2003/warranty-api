from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Product, Serial
from app.schemas.warranty import WarrantyResponse

router = APIRouter(prefix="/warranty", tags=["Warranty"])


@router.get("/{serial_no}", response_model=WarrantyResponse)
def check_warranty(
    serial_no: str,
    db: Annotated[Session, Depends(get_db)],
) -> WarrantyResponse:
    serial = db.scalar(select(Serial).where(Serial.serial_no == serial_no))
    if not serial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serial not found",
        )

    product = serial.product or db.get(Product, serial.product_id)
    product_name = product.name if product else "Unknown"

    today = date.today()
    is_valid = False
    if serial.status == "activated" and serial.warranty_end is not None:
        is_valid = serial.warranty_end >= today

    return WarrantyResponse(
        product_name=product_name,
        status=serial.status,
        activated_at=serial.activated_at,
        warranty_end=serial.warranty_end,
        is_valid=is_valid,
    )

