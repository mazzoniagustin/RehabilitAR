from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID

CLASS_DURATION_MINUTES = 60


# ── Clase INDIVIDUAL ──────────────────────────────────────────────────────────
# Una sesión puntual con fecha y hora exactas. Duración fija: 1 hora.
# Waitlist: FIFO puro, sin prioridades.

class IndividualClassCreate(BaseModel):
    room_id: UUID
    activity_type: Literal[
        'TREN_SUPERIOR',
        'TREN_MEDIO',
        'TREN_INFERIOR'
    ]
    max_capacity: int = Field(gt=0, description='El cupo debe ser mayor a 0.')
    start_time: datetime
    professor_id: Optional[UUID] = None

    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, value):
        end_minutes = value.hour * 60 + value.minute + CLASS_DURATION_MINUTES
        if end_minutes > 22 * 60:
            raise ValueError(
                'La clase debe finalizar antes de las 22:00. '
                'El horario de inicio máximo es las 21:00.'
            )
        return value


# ── Clase FIJA ────────────────────────────────────────────────────────────────
# Se elige un día de la semana y horario; el sistema genera una instancia
# por cada ocurrencia de ese día en el mes en curso (o próximo si ya pasó).
# Duración fija: 1 hora. Waitlist: FIFO con prioridad (ABONADO > NO_ABONADO).

class FijaClassCreate(BaseModel):
    room_id: UUID
    activity_type: Literal[
        'TREN_SUPERIOR',
        'TREN_MEDIO',
        'TREN_INFERIOR'
    ]
    max_capacity: int = Field(gt=0, description='El cupo debe ser mayor a 0.')
    # 0=Lunes … 4=Viernes
    day_of_week: Literal[0, 1, 2, 3, 4]
    start_hour: int = Field(ge=8, le=21, description='Hora de inicio (8–21).')
    start_minute: int = Field(default=0, ge=0, le=59, description='Minuto de inicio.')
    professor_id: Optional[UUID] = None

    @field_validator('start_hour')
    @classmethod
    def validate_start_hour(cls, value, info):
        start_minute = info.data.get('start_minute', 0)
        end_minutes = value * 60 + start_minute + CLASS_DURATION_MINUTES
        if end_minutes > 22 * 60:
            raise ValueError(
                'La clase debe finalizar antes de las 22:00. '
                'El horario de inicio máximo es las 21:00.'
            )
        return value


# ── Responses y helpers compartidos ──────────────────────────────────────────

class ClassResponse(BaseModel):
    id: UUID
    room_id: UUID
    professor_id: Optional[UUID]
    type: str
    activity_type: str
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
