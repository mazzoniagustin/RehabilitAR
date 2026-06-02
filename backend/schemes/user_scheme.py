from sqlite3 import Date

from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

#Valida los datos ingresados, es un template. Si falta alto del User register, no se registra


class UserRegister(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: int
    birth_date: Date
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegisterByStaff(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: int
    birth_date: Date


class AproveCertificate(BaseModel):
    id: str

class RejectCertificate(BaseModel):
    id: str
    reason: str = Field(min_length=1)

class EmployeeRegisterByAdmin(BaseModel):
    name: str
    surname: str
    email: EmailStr
    dni: int
    birth_date: Date
    rol: Literal['ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR']
    specialty: Optional[str] = None  # Solo obligatorio para RECEPCIONISTA y PROFESOR

class RecoverPassword(BaseModel):
    email: EmailStr

class ChangePassword(BaseModel):
    current_password: str = Field(min_length=6)
    new_password: str = Field(min_length=6)
    confirm_new_password: str = Field(min_length=6)

class ResetPassword(BaseModel):
    token: str
    password: str = Field(min_length=6)

class LogOut(BaseModel):
    user_id: str

class ActionReason(BaseModel):
    reason: str = Field(min_length=1, description="Motivo de la acción. Obligatorio para bloqueos y rechazos de desbloqueo.")

class UserBaseResponse(BaseModel):
    id: str
    name: str
    surname: str
    email: str
    dni: int
    phone: Optional[str] = None
    rol: str
    birth_date: Date
    age: Optional[int] = None
    gender: Optional[str] = None
    account_status: str

class ClientResponse(UserBaseResponse):
    credits: Optional[int] = None
    

class StaffResponse(UserBaseResponse):
    specialty: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    #marital_status: Literal['SOLTERO/A', 'CASADO/A', 'DIVORCIADO/A', 'VIUDO/A'] = None
    age: Optional[int] = None
    gender: Optional[Literal['MASCULINO', 'FEMENINO', 'OTRO']] = None

class UserAdminUpdate(BaseModel):
    name:      Optional[str] = None
    surname:   Optional[str] = None
    phone:     Optional[str] = None
    address:   Optional[str] = None
    gender:    Optional[Literal['MASCULINO', 'FEMENINO', 'OTRO']] = None
    rol:       Optional[str] = None
    specialty: Optional[str] = None

class UserResponseByAdmin(BaseModel):
    name: str
    surname: str
    birth_date: Date
    email: EmailStr
    dni: int
    rol: str
    account_status: str
    phone: Optional[str] = None
    credits: Optional[int] = None