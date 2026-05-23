import smtplib
from email.message import EmailMessage
import os

acc_password = os.getenv('acc_password')

def send_account_created_email(to_email: str, name: str, password: str):
    msg = EmailMessage()
    msg['Subject'] = 'Cuenta creada en RehabilitAR'
    msg['From'] = 'RehabilitAR.faq@gmail.com'
    msg['To'] = to_email
    msg.set_content(f'Hola {name},\n\nTu cuenta ha sido creada exitosamente.
    \n\nTu contraseña es: {password}.
    \n\nRecordá cambiar tu contraseña a una de tu preferencia
    \n\nSaludos,\nEl equipo de RehabilitAR')

    try:
        with smtplib.SMTP('smtp.gmail.com', 456) as smtp:
            smtp.login('RehabilitAR.faq@gmail.com', acc_password)
            smtp.send_message(msg)
        
    except Exception as e:
        print(f'Error al enviar el correo: {e}')