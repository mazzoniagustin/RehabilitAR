from fastapi import HTTPException
from utils.notifications import send_account_created_email
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
            'physical_certificate': 'PENDIENTE',
            'account_status': 'ACTIVA',
            'failed_attempts': 0                
        }).execute()
        
        send_account_created_email(data.email, data.name, password)

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
        if response.data[0]['physical_certificate'] == 'APROBADO':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido aprobado.')
            
        supabase.table('users').update({'physical_certificate': 'APROBADO'}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico aprobado.'}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al aprobar el certificado físico.')
    
def reject_certificate(data, reason):
    try:
        reason_text = reason.reason if hasattr(reason, 'reason') else reason
        response = supabase.table('users').select('physical_certificate').eq('id', data.id).execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0]['physical_certificate'] == 'RECHAZADO':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido rechazado.')
            
        supabase.table('users').update({
            'physical_certificate': 'RECHAZADO',
            'physical_rejection_reason': reason_text}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico rechazado.'}

    except HTTPException:
        raise   
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al rechazar el certificado físico.')

def get_filtered_users(name: str = None, role: str = None, status: str = None):
    try:
        response = supabase.table('users').select('id, name, surname, email, dni, rol, account_status, specialty, credits, age, gender')
        
        if name:
            response = response.ilike('name', f'%{name}%')
        if role:
            response = response.eq('rol', role)
        if status:
            response = response.eq('account_status', status)
            
        response = response.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al obtener los usuarios: {str(e)}')


def reject_unblock_request(user_id, reason, acted_by):
    try:
        reason_text = reason.reason if hasattr(reason, 'reason') else reason
        response = supabase.table('users').select('account_status').eq('id', user_id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data['account_status'] == 'ACTIVA':
            raise HTTPException(status_code=400, detail='La cuenta ya está activa.')
            
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': response.data['account_status'],
            'new_status': response.data['account_status'],
            'reason': reason_text,
            'acted_by': acted_by
            }).execute()
        return {'Mensaje': 'Solicitud de reactivacion rechazada.'}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al rechazar la solicitud de reactivacion.')

def approve_unblock_request(user_id, acted_by):
    try:
        response = supabase.table('users').select('account_status').eq('id', user_id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data['account_status'] == 'ACTIVA':
            raise HTTPException(status_code=400, detail='La cuenta ya está activa.')
            
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': response.data['account_status'],
            'new_status': 'ACTIVA',
            'reason': 'Solicitud de reactivacion aprobada.',
            'acted_by': acted_by
            }).execute()
        
        supabase.table('users').update({'account_status': 'ACTIVA'}).eq('id', user_id).execute()
        return {'Mensaje': 'Solicitud de reactivacion aprobada.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al aprobar la solicitud de reactivacion.')

def block_user(user_id, reason, acted_by):
    try:
        reason_text = reason.reason if hasattr(reason, 'reason') else reason
        response = supabase.table('users').select('account_status').eq('id', user_id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data['account_status'] == 'SUSPENDIDA':
            raise HTTPException(status_code=400, detail='La cuenta ya está suspendida.')
            
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': response.data['account_status'],
            'new_status': 'SUSPENDIDA',
            'reason': reason_text,
            'acted_by': acted_by
            }).execute()
        
        supabase.table('users').update({
            'account_status': 'SUSPENDIDA',
            'block_reason': reason_text
            }).eq('id', user_id).execute()
        return {'Mensaje': 'Usuario suspendido.'}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR REAL: {str(e)}")
        raise HTTPException(status_code=400, detail=f'Error al suspender el usuario.')
     
    
def get_pending_certificates():
    try:
        response = (
        supabase.table('users').select
        ('id, name, surname, email, dni')
        .eq('physical_certificate', 'PENDIENTE')
        .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al obtener los certificados pendientes.')

def get_pending_unblock_requests():
    try:
        res = supabase.table('user_status_history')\
            .select('''
                id,
                user_id, 
                reason, 
                created_at, 
                users!user_status_history_user_id_fkey(name, surname, email, account_status)
            ''')\
            .ilike('reason', 'SOLICITUD DE DESBLOQUEO%')\
            .order('created_at', desc=True)\
            .execute()
        
        result = []
        for item in res.data:
            
            user_info = item.get('users!user_status_history_user_id_fkey')
            
            if not user_info:
                user_info = item.get('users')
            
            if user_info and user_info.get('account_status') == 'SUSPENDIDA':
                
                result.append({
                    'user_id': item['user_id'],
                    'reason': item['reason'],
                    'created_at': item['created_at'],
                    'name': user_info['name'],
                    'surname': user_info['surname'],
                    'email': user_info['email']
                })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener solicitudes: {str(e)}")
    


def unblock_user(user_id, acted_by):
    try:
        response = supabase.table('users').select('account_status').eq('id', user_id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data['account_status'] == 'ACTIVA':
            raise HTTPException(status_code=400, detail='La cuenta ya está activa.')
            
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': response.data['account_status'],
            'new_status': 'ACTIVA',
            'reason': 'Cuenta reactivada por Administración.',
            'acted_by': acted_by
            }).execute()
        
        supabase.table('users').update({'account_status': 'ACTIVA'}).eq('id', user_id).execute()
        return {'Mensaje': 'Cuenta reactivada.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al desbloquear el usuario.')

def view_certificate(user_id):
    try:
        response = (
        supabase.table('users').select('physical_certificate_url')
        .eq('id', user_id)
        .single()
        .execute()
        )
        
        if not response.data:
            raise HTTPException(status_code=404, detail='Certificado no encontrado.')
        
        path = response.data.get('physical_certificate_url')
        
        url = supabase.storage.from_('certificates').create_signed_url(path, 300)   
        
        return {'url': url['signedURL']}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al obtener el certificado.')
