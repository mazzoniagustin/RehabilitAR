from fastapi import HTTPException
from utils.permissions import check_user_existance, user_data_validators
from database import supabase, supabase_admin

#Aplicacion de las reglas de negocio.

def register_user(data):
    try:
        
        
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail='La contraseña debe tener al menos 6 caracteres.')

        user_data_validators(data)

        check_user_existance(data.email)
        
        auth_response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password
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
            'failed_attempts': 0,
            'birth_date': data.birth_date.isoformat()          
        }).execute()
        
        return {"Mensaje": "Usuario registrado exitosamente. Queda pendiente de verificación del apto físico."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error en el registro del usuario: {str(e)}')
        
def login_user(email,password):
    
    try:   
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })

        if not response.session:
            raise HTTPException(status_code=401, detail='Credenciales inválidas.')

        user_id = response.user.id
        
        current_status = supabase.table('users').select('account_status').eq('id', user_id).single().execute()
        
        if not current_status.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        supabase.table('users').update({'failed_attempts': 0}).eq('id', user_id).execute() 
        return {'Mensaje': 'Usuario autenticado exitosamente', 'Token': response.session.access_token}
    
    except HTTPException:
        raise
    except Exception:
        # Manejo de intentos fallidos
        user_response = supabase.table('users').select('failed_attempts').eq('email', email).execute()
        
        if user_response.data:  
            failed_attempts = user_response.data[0]['failed_attempts'] + 1
            
            supabase.table('users').update({'failed_attempts': failed_attempts}).eq('email', email).execute()
            
            if failed_attempts >= 5:
                raise HTTPException(status_code=401, detail='Demasiados intentos fallidos. Intente restaurar su contraseña.')
        
        raise HTTPException(status_code=400, detail=f'Credenciales incorrectas.')


def recover_password(email):
    try:
        supabase.auth.reset_password_for_email(
            email,
            {
                'redirect_to': 'http://localhost:8000/frontend/reset-password.html'
            })
        return {'Mensaje': 'Correo de recuperación de contraseña enviado exitosamente.'}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al enviar el correo de recuperación: {str(e)}')

def reset_password(token, password):
    try:
        if not supabase_admin:
            raise HTTPException(
                status_code=500,
                detail='Falta configurar SUPABASE_SERVICE_ROLE_KEY para actualizar contraseñas.'
            )
        user_response = supabase.auth.get_user(token)
        user_id = user_response.user.id
        supabase_admin.auth.admin.update_user_by_id(user_id, {'password': password})
        return {'Mensaje': 'Contraseña actualizada exitosamente.'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al actualizar la contraseña: {str(e)}')


def log_out():
    try:
        supabase.auth.sign_out() 
        return {'Mensaje': 'Usuario desconectado exitosamente.'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al cerrar sesión.')
