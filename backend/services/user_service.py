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
            .select('id, name, surname, email, dni, phone, rol, gender, address, account_status, specialty, physical_certificate, birth_date')
            .eq('id', user_id).single() 
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado')

        user = res.data
        
        age = None
        if user.get('birth_date'):
            born = datetime.fromisoformat(user['birth_date'])
            today = datetime.now()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        base = {
            'id': user.get('id'),
            'name': user.get('name'),
            'surname': user.get('surname'),
            'email': user.get('email'),
            'dni': user.get('dni'),
            'phone': user.get('phone'),
            'rol': user.get('rol'),
            'age': age,
            'gender': user.get('gender'),
            'address': user.get('address'),
            'account_status': user.get('account_status'),
            'physical_certificate': user.get('physical_certificate'),
            'birth_date': user.get('birth_date')
        }

        if user['rol'] == 'ABONADO':
            credits_res = supabase.table('credits').select('available_credits').eq('user_id', user_id).single().execute()
            
            base['credits'] = credits_res.data.get('available_credits') if credits_res.data else 0
            
            subscription_res = supabase.table('subscriptions').select('end_date').eq('user_id', user_id).single().execute()
            base['subscription_expiry'] = subscription_res.data.get('end_date') if subscription_res.data else None

        if user['rol'] in ('ADMINISTRATIVO', 'RECEPCIONISTA', 'PROFESOR'):
            base['specialty'] = user.get('specialty')
        
        if user['rol'] == 'PROFESOR':
            classes_res = supabase.table('classes').select('id', count='exact').eq('professor_id', user['id']).execute()
            base['total_classes'] = classes_res.count if classes_res.count is not None else 0
        
        if user['rol'] in ['RECEPCIONISTA','ADMINISTRATIVO']:
            count_users_res = supabase.table('users').select('id', count='exact').execute()
            base['total_users'] = count_users_res.count if count_users_res.count is not None else 0
        
        if user['rol'] in ['ABONADO', 'NO_ABONADO']:
           reservations_res = supabase.table('reservations').select('id', count='exact').eq('user_id', user['id']).execute()
           base['total_reservations'] = reservations_res.count if reservations_res.count is not None else 0
           
           attendance_res = supabase.table('attendance').select('id, status').eq('user_id', user['id']).execute()
           base['total_absences'] = sum(1 for a in attendance_res.data if a['status'] == 'AUSENTE')
        
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

    
PUBLIC_FIELDS = 'id, name, surname, rol, gender'

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
            .select(PUBLIC_FIELDS, 'birth_date')
            .eq('id', user_id)
            .single()
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        
        base = res.data
        
        age = None
        if base.get('birth_date'):
            born = datetime.fromisoformat(res['birth_date'])
            today = datetime.now()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        base = {
            'id': res.data.get('id'),
            'name': res.data.get('name'),
            'surname': res.data.get('surname'),
            'rol': res.data.get('rol'),
            'gender': res.data.get('gender'),
            'age': age
        }
        
        return base
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error interno. {e}')
    
def show_user_admin_info(user_id: str):
    try:
        res = (
            supabase.table('users')
            .select('id, name, surname, email, dni, phone, rol, gender, address, account_status, birth_date, credits(available_credits), specialty, physical_certificate, physical_certificate_url')
            .eq('id', user_id)
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        
        data = res.data
        
        age = None
        if data.get('birth_date'):
            born = datetime.fromisoformat(data['birth_date'])
            today = datetime.now()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        

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
        data['age'] = age
    
        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error interno. {e}')

def request_unblock(user_id: str, reason):
    try:
        reason_text = reason.reason if hasattr(reason, 'reason') else reason
        
        supabase.table('user_status_history').insert({
            'user_id': user_id,
            'previous_status': 'SUSPENDIDA',
            'new_status': 'SUSPENDIDA', 
            'reason': f'SOLICITUD DE DESBLOQUEO: {reason_text}',
            'acted_by': user_id,
            #'created_at': datetime.now().isoformat(sep=' ', timespec='seconds') lo hace supabase automaticamente
        }).execute()
        return {'Mensaje': 'Solicitud enviada. Un administrador revisará tu caso.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'No se pudo enviar la solicitud. {e}')
