import supabase

def check_permission(admin_id: str, allowed_roles: list[str]):
    current_rol = supabase.table('users').select('rol').eq('id', admin_id).single().execute()

    if current_rol.data and current_rol.data['rol'] in allowed_roles:
        return True
    else:
        return False

def check_user_existance(email: str, dni: str):
    exist_mail = supabase.table('users').select('email').eq('email', email).single().execute()
    if exist_mail.data:
        raise HTTPException(status_code=400, detail='El correo electrónico ya está en uso.')
    else:
        exist_dni = supabase.table('users').select('dni').eq('dni', dni).single().execute()
        if exist_dni.data:
            raise HTTPException(status_code=400, detail='El DNI ya está en uso.')