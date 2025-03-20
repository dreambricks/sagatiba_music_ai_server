from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, field_validator

class UserSchema(BaseModel):
    email: EmailStr
    password_hash: str
    phone: str
    user_info_hash: str  # Hash composto de nome, cpf e data de nascimento
    validated: bool
    created_at: datetime = datetime.now(timezone.utc)

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        import re
        if not re.match(r'^\+?\d{10,15}$', value):
            raise ValueError("Telefone inválido")
        return value
