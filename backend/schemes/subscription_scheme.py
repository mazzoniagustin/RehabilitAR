from pydantic import BaseModel
from uuid import UUID

class Subscription(BaseModel):
    user_id: UUID