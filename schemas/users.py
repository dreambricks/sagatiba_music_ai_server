from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserSchema(BaseModel):
    email: EmailStr
    password_hash: str
    created_at: Optional[datetime] = datetime.now(timezone.utc)