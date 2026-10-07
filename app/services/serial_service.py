import calendar
from datetime import date, datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import Customer, Dealer, Product, Serial, User


def add_months(start_date: date, months: int) -> date:
    """Adds months to a date, correctly adjusting the day for shorter months."""
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    day = min(start_date.day, max_day)
    return date(year, month, day)


def create_single_serial(db: Session, product_id: int, serial_no: str) -> Serial:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    existing = db.scalar(select(Serial).where(Serial.serial_no == serial_no))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Serial number '{serial_no}' already exists",
        )

    serial = Serial(
        product_id=product_id,
        serial_no=serial_no,
        status="in_stock",
    )
    db.add(serial)
    db.commit()
    db.refresh(serial)
    return serial


def create_bulk_serials(
    db: Session,
    product_id: int,
    prefix: str,
    start_no: int,
    end_no: int,
    padding_zeros: int = 0,
) -> Tuple[int, List[Serial]]:
    if start_no > end_no:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_no must be less than or equal to end_no",
        )

    count = end_no - start_no + 1
    if count > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create more than 1000 serials per bulk request",
        )

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Generate serial numbers
    generated_serials: List[str] = []
    for num in range(start_no, end_no + 1):
        if padding_zeros > 0:
            num_str = str(num).zfill(padding_zeros)
        else:
            num_str = str(num)
        generated_serials.append(f"{prefix}{num_str}")

    # Check for existing serials in DB
    existing_in_db = db.scalars(
        select(Serial.serial_no).where(Serial.serial_no.in_(generated_serials))
    ).all()
    if existing_in_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The following serial numbers already exist: {', '.join(existing_in_db[:5])}...",
        )

    # Bulk insert
    new_serials: List[Serial] = [
        Serial(product_id=product_id, serial_no=sn, status="in_stock")
        for sn in generated_serials
    ]
    db.add_all(new_serials)
    db.commit()
    for s in new_serials:
        db.refresh(s)

    return len(new_serials), new_serials


def get_serial_by_no(db: Session, serial_no: str, current_user: User) -> Serial:
    serial = db.scalar(select(Serial).where(Serial.serial_no == serial_no))
    if not serial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serial not found",
        )

    # Dealer scoping: serial of another dealer is considered non-existent (404)
    if current_user.role == "dealer":
        if serial.dealer_id != current_user.dealer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Serial not found",
            )

    return serial


def list_serials(
    db: Session,
    current_user: User,
    status_filter: Optional[str] = None,
    product_id: Optional[int] = None,
    dealer_id: Optional[int] = None,
    q: Optional[str] = None,
    page: int = 1,
    size: int = 10,
) -> Tuple[int, List[Serial]]:
    query = select(Serial)
    count_query = select(func.count(Serial.id))

    # Dealer scoping: dealers only see their own dealer's serials
    if current_user.role == "dealer":
        query = query.where(Serial.dealer_id == current_user.dealer_id)
        count_query = count_query.where(Serial.dealer_id == current_user.dealer_id)
    elif dealer_id is not None:
        query = query.where(Serial.dealer_id == dealer_id)
        count_query = count_query.where(Serial.dealer_id == dealer_id)

    if status_filter:
        query = query.where(Serial.status == status_filter)
        count_query = count_query.where(Serial.status == status_filter)

    if product_id is not None:
        query = query.where(Serial.product_id == product_id)
        count_query = count_query.where(Serial.product_id == product_id)

    if q:
        query = query.where(Serial.serial_no.ilike(f"%{q}%"))
        count_query = count_query.where(Serial.serial_no.ilike(f"%{q}%"))

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(Serial.id.desc()).offset((page - 1) * size).limit(size)
    ).all()

    return total, list(items)


def ship_serial(db: Session, serial_no: str, dealer_id: int) -> Serial:
    serial = db.scalar(select(Serial).where(Serial.serial_no == serial_no))
    if not serial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serial not found",
        )

    # State transition validation: must be in_stock
    if serial.status != "in_stock":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot ship serial: current status is '{serial.status}', expected 'in_stock'",
        )

    dealer = db.get(Dealer, dealer_id)
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dealer not found",
        )

    serial.status = "shipped"
    serial.dealer_id = dealer_id
    serial.shipped_at = datetime.now()

    db.commit()
    db.refresh(serial)
    return serial


def activate_serial(
    db: Session,
    serial_no: str,
    current_user: User,
    customer_id: int,
    input_activated_at: Optional[date] = None,
) -> Serial:
    serial = db.scalar(select(Serial).where(Serial.serial_no == serial_no))
    if not serial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serial not found",
        )

    # Dealer authorization check:
    # "Dealer chỉ activate serial có dealer_id là đại lý của mình (sai trả 403)"
    if current_user.role == "dealer":
        if serial.dealer_id != current_user.dealer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You can only activate serials belonging to your dealership",
            )

    # State transition validation: must be shipped
    if serial.status != "shipped":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot activate serial: current status is '{serial.status}', expected 'shipped'",
        )

    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Date validation: default today, cannot be in future
    today = date.today()
    if input_activated_at is None:
        act_date = today
    else:
        if input_activated_at > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation date cannot be in the future",
            )
        act_date = input_activated_at

    product = serial.product
    if not product:
        product = db.get(Product, serial.product_id)

    warranty_end_date = add_months(act_date, product.warranty_months)

    serial.status = "activated"
    serial.customer_id = customer_id
    serial.activated_at = act_date
    serial.warranty_end = warranty_end_date

    db.commit()
    db.refresh(serial)
    return serial

