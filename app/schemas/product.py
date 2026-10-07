from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    warranty_months: int = Field(..., gt=0, description="Warranty duration in months, must be > 0")


class ProductUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    warranty_months: Optional[int] = Field(None, gt=0)


class ProductResponse(BaseModel):
    id: int
    code: str
    name: str
    warranty_months: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

