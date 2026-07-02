import smtplib
from email.message import EmailMessage
import os
import mimetypes

acc_password = os.getenv('acc_password')

def send_email(to_email: str, subject: str, body: str, attachment_path: str = None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'RehabilitAR <rehabilitar.faq@gmail.com>'
    msg['To'] = to_email
    msg.set_content(body)

    if attachment_path:
        try:
            mime_type, _ = mimetypes.guess_type(attachment_path)
            maintype, subtype = (mime_type or 'application/octet-stream').split('/', 1)

            with open(attachment_path, 'rb') as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(attachment_path)
                )
        except Exception as e:
            print(f'Error al adjuntar archivo: {e}')

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login('rehabilitar.faq@gmail.com', acc_password)
            smtp.send_message(msg)
    except Exception as e:
        print(f'Error al enviar el correo: {e}')



def send_account_created_email(to_email: str, name: str, password: str):
    
    send_email(
        to_email=to_email,
        subject='Cuenta creada en RehabilitAR',
        body=f"""Hola {name},

        Tu cuenta ha sido creada exitosamente.

        Usuario: {to_email}
        Contraseña temporal: {password}

        ⚠️ Te recomendamos cambiar tu contraseña al ingresar.

        Saludos,
        Equipo RehabilitAR
        """
    )
    
def send_account_suspended_email(to_email: str, name: str, reason: str):
    
    send_email(
        to_email=to_email,
        subject='Tu cuenta se encuentra suspendida.',
        body=f"""Hola {name},

        Tu cuenta ha sido suspendida por la administración.

        Motivo: {reason}

        Para volver a tener acceso a las funciones de nuestro centro, solicitá la reactivación dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )
    
def send_account_reactivated_email(to_email: str, name: str):
    
    send_email(
        to_email=to_email,
        subject='Tu cuenta ha sido reactivada.',
        body=f"""Hola {name},

        Tu cuenta ha sido reactivada por la administración.

        Ya podes disfrutar de nuestras actividades nuevamente!

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_account_reactivation_approved(to_email: str, name: str):
    
    send_email(
        to_email=to_email,
        subject='Tu cuenta ha sido reactivada.',
        body=f"""Hola {name},

        Tu solicitud de reactivación ha sido aprobada por administración.

        Ya podes disfrutar de nuestras actividades nuevamente!

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_account_reactivation_rejected(to_email: str, name: str, reason: str):
    
    send_email(
        to_email=to_email,
        subject='Tu solicitud de reactivación ha sido rechazada.',
        body=f"""Hola {name},

        Tu solicitud de reactivación ha sido rechazada por administración.
        
        Motivo: {reason}

        Podes realizar nuevamente tu solicitud de reactivación dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_profile_edited_by_admin(to_email: str, name: str):
    
    send_email(
        to_email=to_email,
        subject='Tu perfil ha sido editado por un administrador.',
        body=f"""Hola {name},

        Tu perfil ha sido editado por un administrador.

        Por favor, revisa los cambios realizados.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_physical_certificate_approved(to_email: str, name: str):
    
    send_email(
        to_email=to_email,
        subject='Tu apto físico ha sido aprobado.',
        body=f"""Hola {name},

        Tu apto físico ha sido aprobado.

        Ya podes realizar actividades!

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_physical_certificate_rejected(to_email: str, name: str, reason: str):
    
    send_email(
        to_email=to_email,
        subject='Tu apto físico ha sido rechazado.',
        body=f"""Hola {name},

        Tu apto físico ha sido rechazado.
        
        Motivo: {reason}
        

        Podes subir nuevamente tu apto físico dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

