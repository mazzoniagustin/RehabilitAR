from fastapi import HTTPException
from utils.notifications import *
from utils.password_utils import random_password
from database import supabase, supabase_admin
from utils.permissions import check_user_existance, user_data_validators, validate_person_name, validate_reason, validate_specialty
from services.notifications_service import create_notification
#Aplicacion de las reglas de negocio.


def _auth_admin_client():
    if not supabase_admin:
        raise HTTPException(
            status_code=500,
            detail='Falta configurar SUPABASE_SERVICE_ROLE_KEY para crear usuarios desde administración.'
        )
    return supabase_admin
 
def register_user_by_staff(data):
    try:
        
        
        check_user_existance(data.email) 
        
        user_data_validators(data)
        
        password = random_password()   
        auth_response = _auth_admin_client().auth.admin.create_user({
            'email': data.email, 
            'password': password
        })
            
            
        if not auth_response:
            raise HTTPException(status_code=400, detail='Error en el registro del usuario.')
 
        user_id = auth_response.user.id
        _auth_admin_client().auth.admin.update_user_by_id(user_id, {'email_confirm': True})
        
        supabase.table('users').insert({
            'id': user_id,
            'name': data.name,
            'surname': data.surname,
            'email': data.email,
            'dni': data.dni,
            'rol': 'NO_ABONADO',
            'physical_certificate': 'PENDIENTE',
            'account_status': 'ACTIVA',
            'birth_date': data.birth_date.isoformat(),
            'failed_attempts': 0                
        }).execute()
        
        send_account_created_email(data.email, data.name, password)
 
        return {"Mensaje": "Usuario registrado exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del usuario. {str(e)}') 
        
def register_employee_by_admin(data):
    try:
        
        check_user_existance(data.email)
        
        user_data_validators(data)
 
        if data.rol in ROLES_WITH_SPECIALTY:
            if not data.specialty:
                raise HTTPException(status_code=400, detail='La especialidad es obligatoria para recepcionistas y profesores.')
            data.specialty = validate_specialty(data.specialty)
        else:
            data.specialty = None
            
        password = random_password()
        response = _auth_admin_client().auth.admin.create_user({
            'email': data.email,
            'password': password
        })
 
        if not response:
            raise HTTPException(status_code=400, detail='Error en el registro del empleado.')
 
        user_id = response.user.id
        _auth_admin_client().auth.admin.update_user_by_id(user_id, {'email_confirm': True})
        
        supabase.table('users').insert({
            'id': user_id,
            'name': data.name,
            'surname': data.surname,
            'email': data.email,
            'dni': data.dni,
            'rol': data.rol,
            'account_status': 'ACTIVA',
            'specialty': data.specialty,
            'failed_attempts': 0,
            'birth_date': data.birth_date.isoformat()
        }).execute()
 
        send_account_created_email(data.email, data.name, password)
        return {"Mensaje": "Empleado registrado exitosamente."}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del empleado. {str(e)}')

ROLES_WITH_SPECIALTY = ['RECEPCIONISTA', 'PROFESOR']

def update_user_by_admin(user_id: str, update_data: dict):
    try:
        if 'name' in update_data:
            update_data['name'] = validate_person_name(update_data['name'], 'Nombre')

        if 'surname' in update_data:
            update_data['surname'] = validate_person_name(update_data['surname'], 'Apellido')

        if 'rol' in update_data:
            if update_data['rol'] in ROLES_WITH_SPECIALTY:
                if not update_data.get('specialty'):
                    raise HTTPException(
                        status_code=400,
                        detail='La especialidad es obligatoria para este rol.'
                    )
            else:
                update_data['specialty'] = None
        if 'specialty' in update_data and update_data['specialty']:
            update_data['specialty'] = validate_specialty(update_data['specialty'])
            
        
        user_data = supabase.table("users").select("email, name").eq('id', user_id).single().execute()
        send_profile_edited_by_admin(user_data.data.get('email'), user_data.data.get('name'))
        create_notification(user_id, "Perfil editado por administración", "Tu perfil ha sido editado por un administrador. Por favor, revisa los cambios realizados.")

        supabase.table("users").update(update_data).eq('id', user_id).execute()
        return {'message': 'Usuario actualizado correctamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al actualizar el usuario: {str(e)}')
 
 
def approve_certificate(data):
    try:
        response = supabase.table('users').select('physical_certificate, email, name').eq('id', data.id).execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0]['physical_certificate'] == 'APROBADO':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido aprobado.')
        
        send_physical_certificate_approved(response.data[0]['email'], response.data[0]['name'])
        create_notification(data.id, "Apto físico aprobado", "Tu apto físico ha sido aprobado. Ya podes realizar actividades!")
        supabase.table('users').update({'physical_certificate': 'APROBADO'}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico aprobado.'}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al aprobar el certificado físico. {e}')
    
def reject_certificate(data):
    try:
        reason_text = data.reason if hasattr(data, 'reason') else data
        reason_text = validate_reason(reason_text)
        response = supabase.table('users').select('physical_certificate, email, name').eq('id', data.id).execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data[0]['physical_certificate'] == 'RECHAZADO':
            raise HTTPException(status_code=400, detail='El apto físico ya ha sido rechazado.')
    
        send_physical_certificate_rejected(response.data[0]['email'], response.data[0]['name'], reason_text)
        create_notification(data.id, "Apto físico rechazado", f"""
                            Tu apto físico ha sido rechazado. 
                            
                            Motivo: {reason_text}. 
                            
                            """)
            
        supabase.table('users').update({
            'physical_certificate': 'RECHAZADO',
            'physical_rejection_reason': reason_text}).eq('id', data.id).execute()
        return {'Mensaje': 'Apto físico rechazado.'}
 
    except HTTPException:
        raise   
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al rechazar el certificado físico. {e}')
 
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
        reason_text = validate_reason(
            reason.reason if hasattr(reason, 'reason') else reason
        )

        response = supabase.table('users')\
            .select('account_status, email, name')\
            .eq('id', user_id)\
            .single()\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        if response.data['account_status'] == 'ACTIVA':
            raise HTTPException(status_code=400, detail='La cuenta ya está activa.')

        supabase.table('user_status_history').update({
            'reason': f'Solicitud rechazada: {reason_text}',
            'request_status': 'REJECTED',
            'acted_by': acted_by
        }).eq('user_id', user_id).eq('request_status', 'PENDING').execute()
        
        send_account_reactivation_rejected(response.data.get('email'), response.data.get('name'), reason_text)
        create_notification(user_id, "Solicitud de reactivación rechazada", f"""Tu solicitud de reactivación ha sido rechazada por administración. 
                            
                            Motivo: {reason_text}. 
                            """)

        return {'Mensaje': 'Solicitud de reactivacion rechazada.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
 
def approve_unblock_request(user_id, acted_by):
    try:
        response = supabase.table('users')\
            .select('account_status, email, name')\
            .eq('id', user_id)\
            .single()\
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        if response.data['account_status'] == 'ACTIVA':
            raise HTTPException(status_code=400, detail='La cuenta ya está activa.')

        update_res = supabase.table('user_status_history')\
            .update({
                'new_status': 'ACTIVA',
                'reason': 'Solicitud de reactivacion aprobada.',
                'request_status': 'APPROVED',
                'acted_by': acted_by
            })\
            .eq('user_id', user_id)\
            .execute()
        print("Filas actualizadas:", update_res.data)
        supabase.table('users')\
            .update({'account_status': 'ACTIVA'})\
            .eq('id', user_id)\
            .execute()

        send_account_reactivation_approved(response.data.get('email'), response.data.get('name'))

        create_notification(user_id, "Solicitud de reactivación aprobada", """Tu solicitud de reactivación ha sido aprobada por administración. 
                            Ya podes disfrutar de nuestras actividades nuevamente!""")

        return {'Mensaje': 'Solicitud de reactivacion aprobada.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
 
def block_user(user_id, reason, acted_by):
    try:
        reason_text = validate_reason(
            reason.reason if hasattr(reason, 'reason') else reason
        )
        response = supabase.table('users').select('account_status, email, name').eq('id', user_id).single().execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        if response.data['account_status'] == 'SUSPENDIDA':
            raise HTTPException(status_code=400, detail='La cuenta ya está suspendida.')
            
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': 'ACTIVA',
            'new_status': 'SUSPENDIDA',
            'reason': reason_text,
            'acted_by': acted_by
            }).execute()
        
        supabase.table('users').update({
            'account_status': 'SUSPENDIDA',
            'block_reason': reason_text
            }).eq('id', user_id).execute()
        
        create_notification(user_id, "Cuenta suspendida", f"""Tu cuenta ha sido suspendida por administración. 
                            
                            Motivo: {reason_text}. 
                            
                            """)
        
        send_account_suspended_email(response.data.get('email'), response.data.get('name'), reason_text)
        return {'Mensaje': 'Usuario suspendido.'}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al suspender el usuario. {e}')
     
    
def get_pending_certificates():
    try:
        response = (
        supabase.table('users').select
        ('id, name, surname, email, dni,physical_certificate, physical_certificate_url')
        .eq('physical_certificate', 'PENDIENTE')
        .not_.is_('physical_certificate_url', None)
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
                request_status,
                users!user_status_history_user_id_fkey(name, surname, email)
            ''')\
            .eq('request_status', 'PENDING')\
            .order('created_at', desc=True)\
            .execute()

        if not res.data:
            return []

        result = []

        for item in res.data:
            user = item.get('users!user_status_history_user_id_fkey') or item.get('users')
            if not user:
                print("Item sin user join:", item)
                continue

            result.append({
                'user_id': item['user_id'],
                'reason': item['reason'],
                'created_at': item['created_at'],
                'name': user['name'],
                'surname': user['surname'],
                'email': user['email']
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
 
def unblock_user(user_id, acted_by):
    try:
        response = supabase.table('users').select('account_status, email, name').eq('id', user_id).single().execute()
            
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
        
        send_account_reactivated_email(response.data.get('email'), response.data.get('name'))
        create_notification(user_id, "Cuenta reactivada", """Tu cuenta ha sido reactivada por la administración.                     
                            Ya podes disfrutar de nuestras actividades nuevamente!""")
        
        supabase.table('users').update({'account_status': 'ACTIVA'}).eq('id', user_id).execute()
        return {'Mensaje': 'Cuenta reactivada.'}
 
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al desbloquear el usuario. {e}')
 
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
        
        url = supabase.storage.from_('physical_certificates').create_signed_url(path, 300)   
        
        return {'url': url['signedURL']}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al obtener el certificado. {e}')
