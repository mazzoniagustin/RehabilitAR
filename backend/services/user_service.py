import uuid
from fastapi import HTTPException, UploadFile
from database import supabase

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

def update_user_info(user_id: str, update_data: dict):
    try:
        supabase.table("users").update(update_data).eq('id', user_id).execute()

        return {"mensaje": "Información del usuario actualizada correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Error al actualizar la información del usuario: {str(e)}")
    

def show_profile():
    try:
        roles_info = supabase.table('users').select('id', 'name', 'surname', 'email', 'rol').execute()
        return roles_info.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al obtener los roles de los usuarios: {str(e)}')


ALLOWED_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf"
]


def upload_certificate(user_id: str, file: UploadFile):

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Solo JPG, PNG, WEBP o PDF."
        )

    # nombre único
    file_ext = file.filename.split(".")[-1]
    file_name = f"{user_id}/{uuid.uuid4()}.{file_ext}"

    # subir a storage
    result = supabase.storage.from_("certificates").upload(
        file_name,
        file.file,
        {"content-type": file.content_type}
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail="Error al subir el archivo")

    # obtener URL firmada (privada)
    signed_url = supabase.storage.from_("certificates").create_signed_url(
        file_name, 60 * 60 * 24 * 365
    )

    # guardar en DB
    supabase.table("users").update({
        "physical_certificate_url": signed_url["signedURL"],
        "physical_certificate": "Pendiente"
    }).eq("id", user_id).execute()

    return {"mensaje": "Certificado subido correctamente"}