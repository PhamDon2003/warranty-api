from datetime import date
from typing import Optional
from pydantic import BaseModel


class WarrantyResponse(BaseModel):
    product_name: str
    status: str
    activated_at: Optional[date] = None
    warranty_end: Optional[date] = None
    is_valid: bool

