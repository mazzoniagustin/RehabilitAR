from fastapi import HTTPException
from utils.password_utils import random_password
from utils.permissions import check_user_existance
from database import supabase
#Aplicacion de las reglas de negocio.

def register_user_by_staff(data):
    try:
        check_user_existance(data.email)
        password = random_password()
        auth_response = supabase.auth.admin.create_user({
            'email': data.email, 
            'password': password
        })
            
            
        if not auth_response.user:
            raise HTTPException(status_code=400, detail='Error en el registro del usuario.')

        user_id = auth_response.user.id
        
        supabase.table('users').insert({
            'id': user_id,
            'name': data.name,
            'surname': data.surname,
            'email': data.email,
            'dni': data.dni,
            'rol': 'NO_ABONADO',
            'physical_certificate': 'Pendiente',
            #'physical_certificate_url': data.physical_certificate_url,
            'account_status': 'ACTIVA',
            'failed_attempts': 0                
        }).execute()
                
            #Enviar mail con la contraseña del usuario
                
        return {"Mensaje": "Usuario registrado exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del usuario.') 
        
def register_employee_by_admin(data):
    try:
        
        check_user_existance(data.email)

        if data.rol in ['RECEPCIONISTA', 'PROFESOR'] and not data.specialty:
            raise HTTPException(status_code=400, detail='La especialidad es obligatoria para recepcionistas y profesores.')

        password = random_password()
        response = supabase.auth.admin.create_user({
            'email': data.email,
            'password': password
        })

        if not response:
            raise HTTPException(status_code=400, detail='Error en el registro del empleado.')
        user_id = response.user.id
        
        supabase.table('users').insert({
            'id': user_id,
            'name': data.name,
            'surname': data.surname,
            'email': data.email,
            'dni': data.dni,
            'rol': data.rol,
            'account_status': 'ACTIVA',
            'specialty': data.specialty,
            'failed_attempts': 0
        }).execute()

        return {"Mensaje": "Empleado registrado exitosamente."}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del empleado. {str(e)}')


def approve_certificate(data):
    try:
        response = supabase.table('users').select('physical_certificate').eq('id', data.id).execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0]['physical_certificate'] == 'Aprobado':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido aprobado.')
            
        supabase.table('users').update({'physical_certificate': 'Aprobado'}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico aprobado.'}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al aprobar el certificado físico.')
    
def reject_certificate(data, reason):
    try:
        reason_text = reason.reason if hasattr(reason, 'reason') else reason
        response = supabase.table('users').select('physical_certificate').eq('id', data.id).execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0]['physical_certificate'] == 'Rechazado':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido rechazado.')
            
        supabase.table('users').update({
            'physical_certificate': 'Rechazado',
            'physical_rejection_reason': reason_text}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico rechazado.'}

    except HTTPException:
        raise   
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al rechazar el certificado físico.')