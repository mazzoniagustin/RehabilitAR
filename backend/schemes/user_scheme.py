from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

#Valida los datos ingresados, es un template. Si falta alto del User register, no se registra


class UserRegister(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegisterByStaff(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str


class AproveCertificate(BaseModel):
    id: str

class RejectCertificate(BaseModel):
    id: str
    reason: str = Field(min_length=1)

class EmployeeRegisterByAdmin(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str
    rol: Literal['ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR']
    specialty: Optional[str] = None  # Solo obligatorio para RECEPCIONISTA y PROFESOR

class RecoverPassword(BaseModel):
    email: EmailStr

class ChangePassword(BaseModel):
    new_password: str = Field(min_length=6)
    confirm_new_password: str = Field(min_length=6)

class LogOut(BaseModel):
    user_id: str

class ActionReason(BaseModel):
    reason: str = Field(min_length=1, description="Motivo de la acción. Obligatorio para bloqueos y rechazos de desbloqueo.")


