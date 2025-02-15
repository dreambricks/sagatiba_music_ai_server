from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List, Optional


class GeneratedAudioSchema(BaseModel):
    redis_id: str
    phone: str
    lyrics: str
    audio_urls: List[str]  # Lista de URLs dos áudios gerados
    timestamp: Optional[datetime] = datetime.now(timezone.utc)
