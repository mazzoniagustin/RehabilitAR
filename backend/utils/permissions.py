from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from database import supabase
import os
from datetime import date
import re

NAME_REGEX = re.compile(
    r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]+(?: [A-Za-zÁÉÍÓÚáéíóúÑñ]+)*$"
)

SPECIALTY_REGEX = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$")

security = HTTPBearer()
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        # Validar el token con Supabase
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Token inválido.")

        user_id = response.user.id

        # Obtener el rol desde tu tabla users (una sola query)
        user_data = (
            supabase.table('users')
            .select('rol, account_status')
            .eq('id', user_id)
            .single()
            .execute()
        )

        if not user_data.data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado en el sistema.")

        return {
            "id": user_id,
            "email": response.user.email,
            "rol": user_data.data['rol'],
            "account_status": user_data.data['account_status']
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido.")

def check_permission(allowed_roles: list[str]):

    def permission_checker(current_user: dict = Depends(get_current_user)):

        if current_user['account_status'] == 'SUSPENDIDA':
            raise HTTPException(status_code=403, detail='Acceso denegado. Tu cuenta está suspendida.')

        if current_user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='Acceso denegado. Tu cuenta no se encuentra activa.')

        if current_user['rol'] not in allowed_roles:
            raise HTTPException(status_code=403, detail='Acceso denegado. Permisos insuficientes.')

        return current_user

    return permission_checker

def check_user_existance(email: str):
    exist_mail = supabase.table('users').select('email').eq('email', email).execute()
    if exist_mail.data:
        raise HTTPException(status_code=400, detail='El correo electrónico ya está en uso.')
    
def is_adult(birth_date):

    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    return age >= 18

def validate_person_name(value: str, field: str):
    value = value.strip()
    if not NAME_REGEX.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail=f'{field} inválido.'
        )
    return value

def validate_reason(reason: str):
    
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail='El motivo es obligatorio.')
    
    reason = reason.strip()
    
    if re.fullmatch(r'[\W_]+', reason):
        raise HTTPException(status_code=400, detail='Motivo inválido')
    
    if reason.isdigit():
        raise HTTPException(status_code=400, detail='Motivo inválido')

    return reason

def validate_specialty(specialty: str):
    
    if not specialty or not specialty.strip():
        raise HTTPException(status_code=400, detail='La especialidad es obligatoria para este rol.')

    specialty = specialty.strip()
    
    if not SPECIALTY_REGEX.fullmatch(specialty):
        raise HTTPException(status_code=400, detail='Especialidad inválida.')
    
    return specialty

def user_data_validators(data):
    
    data.name = validate_person_name(data.name, 'Nombre')
    
    data.surname = validate_person_name(data.surname, 'Apellido')
    
    
    if not isinstance(data.dni, int) or data.dni <= 0:
        raise HTTPException(status_code=400, detail='DNI inválido.')
    
    if len(str(data.dni)) < 6:
        raise HTTPException(status_code=400, detail='El DNI debe tener al menos 6 dígitos.')
    
    if data.birth_date >= date.today():
        raise HTTPException(status_code=400, detail='Fecha de nacimiento inválida.')
