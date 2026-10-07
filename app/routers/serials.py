from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_admin, require_dealer_or_admin
from app.db import get_db
from app.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.serial import (
    SerialActivateRequest,
    SerialBulkCreate,
    SerialBulkResponse,
    SerialCreate,
    SerialResponse,
    SerialShipRequest,
)
from app.services import serial_service

router = APIRouter(prefix="/serials", tags=["Serials"])


@router.post("", response_model=SerialResponse, status_code=status.HTTP_201_CREATED)
def create_serial(
    req: SerialCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> SerialResponse:
    serial = serial_service.create_single_serial(
        db=db, product_id=req.product_id, serial_no=req.serial_no
    )
    return SerialResponse.model_validate(serial)


@router.post("/bulk", response_model=SerialBulkResponse, status_code=status.HTTP_201_CREATED)
def create_serials_bulk(
    req: SerialBulkCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> SerialBulkResponse:
    count, serials = serial_service.create_bulk_serials(
        db=db,
        product_id=req.product_id,
        prefix=req.prefix,
        start_no=req.start_no,
        end_no=req.end_no,
        padding_zeros=req.padding_zeros,
    )
    return SerialBulkResponse(
        total_created=count,
        items=[SerialResponse.model_validate(s) for s in serials],
    )


@router.get("", response_model=PaginatedResponse[SerialResponse])
def get_serials(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: Optional[str] = Query(None, description="Filter by serial status"),
    product_id: Optional[int] = Query(None, description="Filter by product id"),
    dealer_id: Optional[int] = Query(None, description="Filter by dealer id (ignored for dealers)"),
    q: Optional[str] = Query(None, description="Search by serial number"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[SerialResponse]:
    total, items = serial_service.list_serials(
        db=db,
        current_user=current_user,
        status_filter=status,
        product_id=product_id,
        dealer_id=dealer_id,
        q=q,
        page=page,
        size=size,
    )
    return PaginatedResponse(
        items=[SerialResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{serial_no}", response_model=SerialResponse)
def get_serial(
    serial_no: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SerialResponse:
    serial = serial_service.get_serial_by_no(
        db=db, serial_no=serial_no, current_user=current_user
    )
    return SerialResponse.model_validate(serial)


@router.post("/{serial_no}/ship", response_model=SerialResponse)
def ship_serial_endpoint(
    serial_no: str,
    req: SerialShipRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> SerialResponse:
    serial = serial_service.ship_serial(
        db=db, serial_no=serial_no, dealer_id=req.dealer_id
    )
    return SerialResponse.model_validate(serial)


@router.post("/{serial_no}/activate", response_model=SerialResponse)
def activate_serial_endpoint(
    serial_no: str,
    req: SerialActivateRequest,
    current_user: Annotated[User, Depends(require_dealer_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> SerialResponse:
    serial = serial_service.activate_serial(
        db=db,
        serial_no=serial_no,
        current_user=current_user,
        customer_id=req.customer_id,
        input_activated_at=req.activated_at,
    )
    return SerialResponse.model_validate(serial)

