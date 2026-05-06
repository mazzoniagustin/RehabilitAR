from fastapi import HTTPException
from database import supabase
from utils.password_utils import random_password

#Aplicacion de las reglas de negocio.

def register_user_by_staff(data):
    try:
        password = random_password()
        auth_response = supabase.auth.admin.create_user({
            'email': data.email, 
            'password': password
        })
            
        if auth_response:
            supabase.table('users').insert({
                'id': auth_response.user.id,
                'name': data.name,
                'surname': data.surname,
                'email': data.email,
                'dni': data.dni,
                'rol': 'NO_ABONADO',
                'dni_photo': data.dni_photo,
                'physical_certificate': 'Pendiente',
                'account_status': 'Activa'
            }).execute()
                
            #Enviar mail con la contraseña del usuario
                
            return {"Mensaje": "Usuario registrado exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del usuario.') 
        
def register_employee_by_admin(data):
    try:
        password = random_password()
        response = supabase.auth.admin.create_user({
            'email': data.email,
            'password': password
        })

        if response:
            supabase.table('users').insert({
                'id': response.user.id,
                'name': data.name,
                'surname': data.surname,
                'email': data.email,
                'dni': data.dni,
                'rol': data.rol,
                'account_status': 'Activa'
            }).execute()

            return {"Mensaje": "Empleado registrado exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del empleado.')

def check_permission(admin_id: str, allowed_roles: list[str]):
    current_rol = supabase.table('users').select('rol').eq('id', admin_id).execute()

    if current_rol.data and current_rol.data[0].get('rol') in allowed_roles:
        return True
    else:
        return False

def approve_certificate(data):
    try:
        response = supabase.table('users').select('physical_certificate').eq('id', data.id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0].get('physical_certificate') == 'Aprobado':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido aprobado.')
            
        supabase.table('users').update({'physical_certificate': 'Aprobado'}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico aprobado.'}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al aprobar el certificado físico.')
    
def reject_certificate(data):
    try:
        response = supabase.table('users').select('physical_certificate').eq('id', data.id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0].get('physical_certificate') == 'Rechazado':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido rechazado.')
            
        supabase.table('users').update({'physical_certificate': 'Rechazado'}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico rechazado.'}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al rechazar el certificado físico.')
        