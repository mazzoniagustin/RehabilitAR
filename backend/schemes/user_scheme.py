from pydantic import BaseModel, EmailStr, Field
from typing import Literal

#Valida los datos ingresados, es un template. Si falta alto del User register, no se registra


class UserRegister(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str
    password: str = Field(min_length=6)
    dni_photo: str
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
    dni_photo: str
    physical_certificate: str

class UserUpdatePhysicalCertificate(BaseModel):
    admin_id: str
    id: str

class EmployeeRegisterByAdmin(BaseModel):
    admin_id: str
    name: str
    surname: str
    email: EmailStr
    dni: str
    rol: Literal['ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR']