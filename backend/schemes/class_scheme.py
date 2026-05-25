from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID


class ClassCreate(BaseModel):
    room_id: UUID
    type: Literal['INDIVIDUAL', 'GRUPAL', 'FIJA']
    activity_type: Literal[
        'TREN_SUPERIOR',
        'TREN_MEDIO',
        'TREN_INFERIOR'
    ]

    is_scheduled: bool = False

    max_capacity: int = Field(
        gt=0,
        description='El cupo debe ser mayor a 0.'
    )

    start_time: datetime
    end_time: datetime

    professor_id: Optional[UUID] = None

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, value, info):
        start_time = info.data.get('start_time')

        if start_time and value <= start_time:
            raise ValueError(
                'La hora de finalizacion debe ser mayor a la hora de inicio.'
            )

        return value


class ClassResponse(BaseModel):
    id: UUID
    room_id: UUID
    professor_id: Optional[UUID]

    type: str
    activity_type: str

    is_scheduled: bool
    status: str

    max_capacity: int
    current_capacity: int

    start_time: datetime
    end_time: datetime


class AssignProfessor(BaseModel):
    professor_id: UUID

class UpdateCapacity(BaseModel):
    new_capacity: int = Field(gt=0, description='El nuevo cupo debe ser mayor a 0.')

class EvaluateRequest(BaseModel):
    status: Literal['ACEPTADA', 'RECHAZADA']
    reason: Optional[str] = None
