from pydantic import BaseModel
from uuid import UUID

class CancelClass(BaseModel):
    class_id: UUID
    cancel_reason: str

class CancelReservation(BaseModel):
    reservation_id: UUID

class CancelSubscription(BaseModel):
    user_id: UUID