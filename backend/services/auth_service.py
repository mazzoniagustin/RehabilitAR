from fastapi import HTTPException
from database import supabase


class AuthService:
    @staticmethod
    def register_user(data):
        try: 
            auth_response = supabase.auth.sign_up({
                "email": data.email,
                "password": data.password
            })
            
            if auth_response:
                supabase.table('users').insert({
                    'id': auth_response.user.id,
                    'name': data.name,
                    'surname': data.surname,
                    'email': data.email,
                    'dni': data.dni,
                    'rol': 'NO_ABONADO',
                    'physical_certificate': 'Pendiente',
                    'account_status': 'Pendiente'
                    #Url del dni?
                }).execute()
                return {"Mensaje": "Usuario registrado exitosamente. Queda pendiente de verificación del apto físico."}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Error en el registro del usuario: {str(e)}')
    @staticmethod    
    def login_user(email,password):
        try:
            response = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            return {'Mensaje:': 'Usuario autenticado exitosamente', 'Token': response.session.access_token}
        except Exception:
            raise HTTPException(status_code=401, detail='Error en las credenciales de inicio de sesión.')