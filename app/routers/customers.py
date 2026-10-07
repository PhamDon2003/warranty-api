from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.dependencies import require_admin, require_dealer_or_admin
from app.db import get_db
from app.models import Customer, Serial, User
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    _: Annotated[User, Depends(require_dealer_or_admin)],
    db: Annotated[Session, Depends(get_db)],
    q: Optional[str] = Query(None, description="Search by customer name or phone"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[CustomerResponse]:
    base_query = select(Customer)
    count_query = select(func.count(Customer.id))

    if q:
        search_filter = or_(
            Customer.name.ilike(f"%{q}%"),
            Customer.phone.ilike(f"%{q}%"),
        )
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = db.scalar(count_query) or 0
    items_query = (
        base_query
        .order_by(Customer.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = db.scalars(items_query).all()

    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    _: Annotated[User, Depends(require_dealer_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> CustomerResponse:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return CustomerResponse.model_validate(customer)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    req: CustomerCreate,
    _: Annotated[User, Depends(require_dealer_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> CustomerResponse:
    customer = Customer(
        name=req.name,
        phone=req.phone,
        email=req.email,
        address=req.address,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    req: CustomerUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> CustomerResponse:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    if req.name is not None:
        customer.name = req.name
    if req.phone is not None:
        customer.phone = req.phone
    if req.email is not None:
        customer.email = req.email
    if req.address is not None:
        customer.address = req.address

    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Check if serials reference this customer
    serial_count = db.scalar(
        select(func.count(Serial.id)).where(Serial.customer_id == customer_id)
    )
    if serial_count and serial_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete customer referenced by serials",
        )

    db.delete(customer)
    db.commit()

