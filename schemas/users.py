from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr

class UserSchema(BaseModel):
    email: EmailStr
    password_hash: str
    created_at: datetime = datetime.now(timezone.utc)