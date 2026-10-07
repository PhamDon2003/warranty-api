from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    dealer_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
