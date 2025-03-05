from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr

class UserSchema(BaseModel):
    email: EmailStr
    password_hash: str
    user_info_hash: str # Hash composto de nome, cpf e data de nascimento
    validated: bool
    created_at: datetime = datetime.now(timezone.utc)