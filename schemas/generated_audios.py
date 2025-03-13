from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, ConfigDict
from bson import ObjectId
from typing import List

class GeneratedAudioSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    redis_id: str
    user_oid: ObjectId
    lyrics_oid: ObjectId
    audio_urls: List[str]  # Lista de URLs dos áudios gerados
    timestamp: datetime = datetime.now(timezone.utc)

    @field_validator("user_oid", "lyrics_oid", mode="before")
    @classmethod
    def validate_objectid(cls, value):
        """Converte strings para ObjectId se necessário."""
        if isinstance(value, str):
            if not ObjectId.is_valid(value):
                raise ValueError("Invalid ObjectId")
            return ObjectId(value)
        return value  # Retorna como está se já for um ObjectId
