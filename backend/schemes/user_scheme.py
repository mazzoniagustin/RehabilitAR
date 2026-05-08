from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

#Valida los datos ingresados, es un template. Si falta alto del User register, no se registra


class UserRegister(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str
    password: str = Field(min_length=6)
    physical_certificate: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegisterByStaff(BaseModel):
    staff_id: str
    name: str
    surname: str
    email: EmailStr
    dni: str
    physical_certificate: str


class AproveCertificate(BaseModel):
    admin_id: str
    id: str

class RejectCertificate(BaseModel):
    admin_id: str
    id: str
    reason: str = Field(min_length=1)

class EmployeeRegisterByAdmin(BaseModel):
    admin_id: str
    name: str
    surname: str
    email: EmailStr
    dni: str
    rol: Literal['ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR']
    specialty: Optional[str] = None  # Solo obligatorio para RECEPCIONISTA y PROFESOR

class RecoverPassword(BaseModel):
    email: EmailStr

class ChangePassword(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=6)
    confirm_new_password: str = Field(min_length=6)
