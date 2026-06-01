from pydantic import BaseModel
from uuid import UUID

class IndividualReservation(BaseModel):
    class_id: UUID
    payment_percentage: int

class RegularReservation(BaseModel):
    class_id: UUID

class WaitlistJoin(BaseModel):
<<<<<<< HEAD
    class_id: UUID
=======
    class_id: UUID
>>>>>>> origin/codex/test-reservas-cancelaciones
