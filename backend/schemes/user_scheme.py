from pydantic import BaseModel, EmailStr, Field
from typing import Literal

class UserRegister(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str
    password: str = Field(min_length=6)
    dni_photo: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegisterByAdmin(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: str
    rol: Literal['ABONADO', 'NO_ABONADO', 'ADMINISTRATIVO', 'RECEPCIONISTA']
    dni_photo: str

class UserUpdatePhysicalCertificate(BaseModel):
    id: str