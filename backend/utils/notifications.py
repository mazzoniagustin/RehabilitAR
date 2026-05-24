import smtplib
from email.message import EmailMessage
import os

acc_password = os.getenv('acc_password')

def send_account_created_email(to_email: str, name: str, password: str):
    msg = EmailMessage()
    msg['Subject'] = 'Cuenta creada en RehabilitAR'
    msg['From'] = 'RehabilitAR <rehabilitar.faq@gmail.com>'
    msg['To'] = to_email

    msg.set_content(
        f"""Hola {name},

        Tu cuenta ha sido creada exitosamente.

        Usuario: {to_email}
        Contraseña temporal: {password}

        ⚠️ Te recomendamos cambiar tu contraseña al ingresar.

        Saludos,
        Equipo RehabilitAR
        """
    )

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls() 
            smtp.login('rehabilitar.faq@gmail.com', acc_password)
            smtp.send_message(msg)

    except Exception as e:
        print(f'Error al enviar el correo: {e}')