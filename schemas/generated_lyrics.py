from datetime import datetime, timezone
from pydantic import BaseModel
from bson import ObjectId as _ObjectId
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated
from typing import Optional

# Validação de ObjectId
def check_object_id(value: str) -> str:
    if not _ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return value

ObjectId = Annotated[str, AfterValidator(check_object_id)]

class GeneratedLyricsSchema(BaseModel):
    lyrics: str
    redis_id: Optional[str]
    user_oid: ObjectId
    timestamp: datetime = datetime.now(timezone.utc)
