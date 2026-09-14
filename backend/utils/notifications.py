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

def send_professor_request_accepted(to_email: str, name: str, class_desc: str):

    send_email(
        to_email=to_email,
        subject='Tu solicitud para dictar una clase fue aceptada.',
        body=f"""Hola {name},

        Tu solicitud para dictar la clase {class_desc} fue aceptada.

        Ya figurás como profesor/a asignado/a a esa clase.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_professor_request_rejected(to_email: str, name: str, class_desc: str, reason: str):

    send_email(
        to_email=to_email,
        subject='Tu solicitud para dictar una clase fue rechazada.',
        body=f"""Hola {name},

        Tu solicitud para dictar la clase {class_desc} fue rechazada.

        Motivo: {reason}

        Podes solicitar otras clases disponibles dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_reservation_confirmed_email(to_email: str, name: str, class_desc: str):

    send_email(
        to_email=to_email,
        subject='Tu reserva fue confirmada.',
        body=f"""Hola {name},

        Te uniste correctamente a la clase de {class_desc}.

        Podes ver el detalle de tu reserva dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_attendance_reminder_email(to_email: str, name: str, class_desc: str):

    send_email(
        to_email=to_email,
        subject='Recordatorio de asistencia a clase.',
        body=f"""Hola {name},

        Te recordamos que tenés una clase reservada de {class_desc}.

        Si no podés asistir, recordá cancelar tu reserva dentro de los plazos establecidos por el centro.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_no_professor_class_email(to_email: str, name: str, class_desc: str):

    send_email(
        to_email=to_email,
        subject='Clase disponible sin profesor asignado.',
        body=f"""Hola {name},

        Hay una clase de {class_desc} que todavía no tiene profesor asignado.

        Si estás disponible, podés solicitar tomarla desde la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_pending_debt_reminder_email(to_email: str, name: str, class_desc: str, amount):

    send_email(
        to_email=to_email,
        subject='Recordatorio de deuda pendiente.',
        body=f"""Hola {name},

        Te recordamos que tenés una deuda pendiente de ${amount} correspondiente a la clase de {class_desc}.

        El saldo restante debe abonarse antes del inicio de la clase.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_subscription_due_soon_email(to_email: str, name: str):

    send_email(
        to_email=to_email,
        subject='Recordatorio de vencimiento de mensualidad.',
        body=f"""Hola {name},

        Te recordamos que estás cerca del vencimiento del plazo para abonar tu mensualidad.

        Tenés tiempo hasta el día 10 del mes para registrar el pago.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_subscription_payment_deadline_expired_email(to_email: str, name: str):

    send_email(
        to_email=to_email,
        subject='Venció el plazo de pago de la mensualidad.',
        body=f"""Hola {name},

        Te informamos que venció el plazo de 10 días para abonar tu mensualidad.

        Regularizá tu situación para evitar restricciones sobre tu cuenta.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_waitlist_joined_email(to_email: str, name: str, class_desc: str, posicion: int):

    send_email(
        to_email=to_email,
        subject='Te uniste a la lista de espera.',
        body=f"""Hola {name},

        Te uniste a la lista de espera de la clase de {class_desc}.

        Tu posición actual es {posicion}.

        Te avisaremos si entrás a la clase por una vacante o si avanzás de posición.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_waitlist_threshold_admin_email(to_email: str, name: str, class_desc: str, total_waitlist: int):

    send_email(
        to_email=to_email,
        subject='Lista de espera con alta demanda.',
        body=f"""Hola {name},

        La lista de espera de la clase de {class_desc} superó los 10 miembros.

        Cantidad actual de personas en lista de espera: {total_waitlist}.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_waitlist_advanced_email(to_email: str, name: str, class_desc: str, posicion: int):

    send_email(
        to_email=to_email,
        subject='Avanzaste en la lista de espera.',
        body=f"""Hola {name},

        Avanzaste de posición en la lista de espera de la clase de {class_desc}.

        Tu posición actual es {posicion}.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_waitlist_promoted_email(to_email: str, name: str, class_desc: str):

    send_email(
        to_email=to_email,
        subject='¡Entraste a la clase!',
        body=f"""Hola {name},

        Se liberó un lugar y entraste a la clase de {class_desc}.

        Podes ver el detalle de tu reserva dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_class_cancelled_credit_email(to_email: str, name: str, class_desc: str, reason: str):

    send_email(
        to_email=to_email,
        subject='Tu clase fue cancelada: se te otorgó un crédito.',
        body=f"""Hola {name},

        Tu clase de {class_desc} fue cancelada.

        Motivo: {reason}

        Como sos cliente abonado, se te otorgó un crédito que podes usar para reservar otra clase.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_class_cancelled_no_credit_email(to_email: str, name: str, class_desc: str, reason: str):

    send_email(
        to_email=to_email,
        subject='Tu clase fue cancelada.',
        body=f"""Hola {name},

        Tu clase de {class_desc} fue cancelada.

        Motivo: {reason}

        Alcanzaste el máximo de créditos disponibles este mes, por lo que no pudimos otorgarte un crédito adicional por esta cancelación.

        Ante cualquier duda, podes contactarte con administración.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_class_cancelled_refund_email(to_email: str, name: str, class_desc: str, reason: str):

    send_email(
        to_email=to_email,
        subject='Tu clase fue cancelada: se procesará tu reembolso.',
        body=f"""Hola {name},

        Tu clase de {class_desc} fue cancelada.

        Motivo: {reason}

        Se procesará el reembolso de tu pago. Te avisaremos cuando esté acreditado.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_reservation_cancelled_by_client_email(to_email: str, name: str, class_desc: str, detalle: str):

    send_email(
        to_email=to_email,
        subject='Cancelaste tu reserva',
        body=f"""Hola {name},

        Tu reserva de {class_desc} fue cancelada con éxito.

        {detalle}

        Podes ver el detalle dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )

def send_waitlist_removed_class_cancelled_email(to_email: str, name: str, class_desc: str, reason: str):

    send_email(
        to_email=to_email,
        subject='Se canceló una clase de tu lista de espera.',
        body=f"""Hola {name},

        La clase de {class_desc}, en la que estabas anotado/a en lista de espera, fue cancelada.

        Motivo: {reason}

        Fuiste removido/a de la lista de espera de esa clase. Podes anotarte a otras clases disponibles dentro de la página web.

        Saludos,
        Equipo RehabilitAR
        """
    )
