from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, ConfigDict
from bson import ObjectId
from typing import Optional

class WorkerEventSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    worker_oid: ObjectId
    action: str  # "accepted_task", "completed_task"
    redis_id: str
    lyrics_oid: ObjectId
    audio_oid: Optional[ObjectId] = None
    timestamp: datetime = datetime.now(timezone.utc)

    @field_validator("worker_oid", "lyrics_oid", "audio_oid", mode="before")
    @classmethod
    def validate_objectid(cls, value):
        """Converte strings para ObjectId se necessário."""
        if isinstance(value, str):
            if not ObjectId.is_valid(value):
                raise ValueError("Invalid ObjectId")
            return ObjectId(value)
        return value  # Retorna como está se já for um ObjectId
