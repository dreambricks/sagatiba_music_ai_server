from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, ConfigDict
from bson import ObjectId
from typing import Optional

class GeneratedLyricsSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    lyrics: str
    redis_id: Optional[str] = None
    user_oid: ObjectId
    timestamp: datetime = datetime.now(timezone.utc)

    @field_validator("user_oid", mode="before")
    @classmethod
    def validate_objectid(cls, value):
        """Converte strings para ObjectId se necessário."""
        if isinstance(value, str):
            if not ObjectId.is_valid(value):
                raise ValueError("Invalid ObjectId")
            return ObjectId(value)
        return value  # Retorna como está se já for um ObjectId
