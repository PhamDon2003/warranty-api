from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SerialCreate(BaseModel):
    product_id: int
    serial_no: str = Field(..., min_length=1, max_length=100)


class SerialBulkCreate(BaseModel):
    product_id: int
    prefix: str = Field(..., min_length=1, max_length=50)
    start_no: int = Field(..., ge=1)
    end_no: int = Field(..., ge=1)
    padding_zeros: int = Field(0, ge=0, le=10, description="Zero padding for serial numbers (e.g. 4 -> 0001)")


class SerialShipRequest(BaseModel):
    dealer_id: int


class SerialActivateRequest(BaseModel):
    customer_id: int
    activated_at: Optional[date] = None


class SerialResponse(BaseModel):
    id: int
    serial_no: str
    product_id: int
    dealer_id: Optional[int] = None
    customer_id: Optional[int] = None
    status: str
    shipped_at: Optional[datetime] = None
    activated_at: Optional[date] = None
    warranty_end: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SerialBulkResponse(BaseModel):
    total_created: int
    items: List[SerialResponse]

