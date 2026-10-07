from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_admin
from app.db import get_db
from app.models import Dealer, Serial, User
from app.schemas.common import PaginatedResponse
from app.schemas.dealer import DealerCreate, DealerResponse, DealerUpdate

router = APIRouter(prefix="/dealers", tags=["Dealers"])


@router.get("", response_model=PaginatedResponse[DealerResponse])
def list_dealers(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[DealerResponse]:
    total = db.scalar(select(func.count(Dealer.id))) or 0
    query = (
        select(Dealer)
        .order_by(Dealer.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    items = db.scalars(query).all()
    return PaginatedResponse(
        items=[DealerResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{dealer_id}", response_model=DealerResponse)
def get_dealer(
    dealer_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DealerResponse:
    dealer = db.get(Dealer, dealer_id)
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dealer not found",
        )
    return DealerResponse.model_validate(dealer)


@router.post("", response_model=DealerResponse, status_code=status.HTTP_201_CREATED)
def create_dealer(
    req: DealerCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> DealerResponse:
    dealer = Dealer(
        name=req.name,
        phone=req.phone,
        address=req.address,
    )
    db.add(dealer)
    db.commit()
    db.refresh(dealer)
    return DealerResponse.model_validate(dealer)


@router.put("/{dealer_id}", response_model=DealerResponse)
def update_dealer(
    dealer_id: int,
    req: DealerUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> DealerResponse:
    dealer = db.get(Dealer, dealer_id)
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dealer not found",
        )

    if req.name is not None:
        dealer.name = req.name
    if req.phone is not None:
        dealer.phone = req.phone
    if req.address is not None:
        dealer.address = req.address

    db.commit()
    db.refresh(dealer)
    return DealerResponse.model_validate(dealer)


@router.delete("/{dealer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dealer(
    dealer_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    dealer = db.get(Dealer, dealer_id)
    if not dealer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dealer not found",
        )

    # Check if serials or users reference this dealer
    serial_count = db.scalar(
        select(func.count(Serial.id)).where(Serial.dealer_id == dealer_id)
    )
    user_count = db.scalar(
        select(func.count(User.id)).where(User.dealer_id == dealer_id)
    )
    if (serial_count and serial_count > 0) or (user_count and user_count > 0):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete dealer referenced by serials or users",
        )

    db.delete(dealer)
    db.commit()
