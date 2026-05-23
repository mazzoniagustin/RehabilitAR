import uuid
from fastapi import HTTPException, UploadFile
from database import supabase
from datetime import datetime

def change_password(data): 
    try:
        if data.new_password != data.confirm_new_password:
            raise HTTPException(status_code=400, detail='Las contraseñas no coinciden.')
        
        response = supabase.auth.update_user({
            'password': data.new_password
        })
        
        if not response.user:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        
        supabase.table('users').update({'failed_attempts': 0}).eq('id', response.user.id).execute()

        return {'Mensaje': 'Contraseña actualizada exitosamente.'}

    except HTTPException:
        raise
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al cambiar la contraseña')

def show_user_info(user_id: str):
    try:
        res = (
            supabase
            .table('users')
            .select('id, name, surname, email, dni, phone, rol, age, gender, address, account_status, credits, specialty')
            .eq('id', user_id).single() 
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado')

        user = res.data 

        base = {
            'id': user.get('id'),
            'name': user.get('name'),
            'surname': user.get('surname'),
            'email': user.get('email'),
            'dni': user.get('dni'),
            'phone': user.get('phone'),
            'rol': user.get('rol'),
            'age': user.get('age'),
            'gender': user.get('gender'),
            'address': user.get('address'),
            'account_status': user.get('account_status'),
        }

        if user['rol'] == 'ABONADO':
            base['credits'] = user.get('credits')

        if user['rol'] in ('ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR'):
            base['specialty'] = user.get('specialty')

        return base

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Error interno: {str(e)}'
        )

def update_user_info(user_id: str, update_data: dict):
    try:
        supabase.table("users").update(update_data).eq('id', user_id).execute()

        return {'mensaje': 'Información del usuario actualizada correctamente'}

    except Exception as e:
        raise HTTPException(status_code=500,detail=f'Error al actualizar la información del usuario: {str(e)}')
    

def show_profile():
    try:
        roles_info = (
        supabase.table('users')
        .select(
            'id, name, surname, email, rol, age, gender, '
            'address, account_status, specialty, '
            'physical_certificate, credits(available_credits)'
        )
            .execute()
        )
        return roles_info.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener los roles de los usuarios: {str(e)}')


ALLOWED_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf"
]

ALLOWED_EXTENSIONS = [
    "jpeg",
    "png",
    "webp",
    "pdf"
]


def upload_certificate(user_id: str, file: UploadFile):
    
    if not file or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, 'Formato inválido.')

    file_ext = file.filename.split('.')[-1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, 'Extensión inválida.')

    try:
        file.file.seek(0)
        file_bytes = file.file.read()
    except Exception:
        raise HTTPException(400, 'No se pudo leer el archivo.')

    if not file_bytes:
        raise HTTPException(400, 'Archivo vacío.')

    file_name = (f'{user_id}/{uuid.uuid4()}.{file_ext}')
    
    try:
        supabase.storage.from_('physical_certificates').upload(
            file_name,
            file_bytes,
            {'content-type': file.content_type}
        )
    except Exception as e:
        raise HTTPException(400, f'Error al subir el archivo: {e}')

    res = supabase.table('users').update({
        'physical_certificate_url': file_name,
        'physical_certificate': 'PENDIENTE'
    }).eq('id', user_id).execute()

    if not res.data:
        raise HTTPException(400, 'No se pudo actualizar el usuario.')

    return {'message': 'Apto físico enviado.', 'status': 'PENDIENTE'}

#def search_users_by_name(name: str):
#    try:
#        response = (
#            supabase.table('users')
#            .select('id, name, surname, email, dni, rol, account_status')
#            .ilike('name', f'%{name}%')
#            .execute()
#        )
#        return response.data
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=f'Error al buscar: {str(e)}')
    
PUBLIC_FIELDS = 'id, name, surname, rol, age, gender'

def search_users_public(name: str = None, role: str = None):
    try:
        response = supabase.table('users').select(PUBLIC_FIELDS)
        
        if role:
            if role == 'ADMINISTRATIVO':
                raise HTTPException(status_code=403, detail='No tienes permisos para buscar personal administrativo.')
            response = response.eq('rol', role)
        else:
            response = response.in_('rol', ['NO_ABONADO', 'ABONADO', 'PROFESOR'])
        
        if name:
            response = response.ilike('name', f'%{name}%')
            
        response = response.execute()
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al buscar usuarios: {str(e)}')

def show_user_public_info(user_id: str):
    try:
        res = (
            supabase.table('users')
            .select(PUBLIC_FIELDS)
            .eq('id', user_id)
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail='Error interno.')
    
def show_user_admin_info(user_id: str):
    try:
        res = (
            supabase.table('users')
            .select('id, name, surname, email, dni, phone, rol, age, gender, address, account_status, credits(available_credits), specialty, physical_certificate')
            .eq('id', user_id)
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        data = res.data

        credits_list = data.pop('credits', []) or []
        date_now = datetime.now()
        current = next (
            (c for c in credits_list 
            if c.get('month') and 
            datetime.fromisoformat(str(c['month'])).month == date_now.month and
            datetime.fromisoformat(str(c['month'])).year == date_now.year),
            None
        )
        data['available_credits'] = current.get('available_credits') if current else 0
        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail='Error interno.')

def request_unblock(user_id: str, reason):
    try:
        reason_text = reason.reason if hasattr(reason, 'reason') else reason
        
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': 'SUSPENDIDO',
            'new_status': 'SUSPENDIDO', 
            'reason': f'SOLICITUD DE DESBLOQUEO: {reason_text}',
            'acted_by': user_id
        }).execute()
        return {'Mensaje': 'Solicitud enviada. Un administrador revisará tu caso.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail='No se pudo enviar la solicitud.')
