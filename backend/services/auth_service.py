from fastapi import HTTPException
from database import supabase

#Aplicacion de las reglas de negocio.

def register_user(data):
    try: 
        auth_response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password
        })

        if auth_response:
            check_user_existance(data.email, data.dni)
            supabase.table('users').insert({
                'id': auth_response.user.id,
                'name': data.name,
                'surname': data.surname,
                'email': data.email,
                'dni': data.dni,
                'rol': 'NO_ABONADO',
                'physical_certificate': 'Pendiente',
                'account_status': 'Activa',                 
            }).execute()
            return {"Mensaje": "Usuario registrado exitosamente. Queda pendiente de verificación del apto físico."}
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
        
        current_status = supabase.table('users').select('failed_attempts', 'account_status').eq('id', response.user.id).single().execute()
        
        if not current_status.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')

        if current_status.data['account_status'] == 'Suspendida':
            raise HTTPException(status_code=403, detail='Cuenta suspendida. Contacte al administrador.')

        supabase.table('users').update({'failed_attempts': 0}).eq('id', response.user.id).execute() 
        return {'Mensaje': 'Usuario autenticado exitosamente', 'Token': response.session.access_token}
    
    except HTTPException:
        raise
    except Exception:

        user = supabase.table('users').select('id', 'failed_attempts').eq('email', email).single().execute()

        if not user.data:
            raise HTTPException(status_code=401, detail='Credenciales inválidas.')

        count = user.data['failed_attempts'] + 1
        supabase.table('users').update({'failed_attempts': count}).eq('email', email).execute()
        if count >= 3:
            raise HTTPException(status_code=401, detail='Se ve que posee dificultades para iniciar sesión. Le recomendamos reestablecer su contraseña.')
        
        raise HTTPException(status_code=401, detail='Error en las credenciales de inicio de sesión.')


# def recover_password(data): falta front para enviar el mail.


"""def change_password(data): Esta función va en user_service.py. Se deja como referencia de cómo se implementa el cambio de contraseña con Supabase.
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
"""

def log_out():
    try:
        supabase.auth.sign_out(scope='local') #Solo cierra la sesión local, no afecta otras.
        return {'Mensaje': 'Usuario desconectado exitosamente.'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Error al cerrar sesión.')