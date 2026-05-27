from database import supabase
from datetime import datetime, timezone
from fastapi import HTTPException
from services.classes_service import cancel_class
from utils import benefits


def _registrar_cancelacion(class_id: str, cancel_reason: str, tipo: str):
    """
    Registra el motivo de cancelación en la tabla 'cancellations',
    que es el lugar correcto en el schema (la tabla classes no tiene
    columna cancellation_reason).
    """
    supabase.table('cancellations').insert({
        'class_id': class_id,
        'reason': cancel_reason,
        'type': tipo,
    }).execute()


def _cancelar_reservas_de_clase(class_id: str):
    """
    Cancela todas las reservas confirmadas de la clase y aplica
    los beneficios correspondientes (crédito a abonados, reembolso
    pendiente de implementar para no abonados).
    """
    reservas = (
        supabase.table('reservations')
        .select('*')
        .eq('class_id', class_id)
        .eq('status', 'CONFIRMADA')
        .execute()
    )
    for reserva in (reservas.data or []):
        supabase.table('reservations').update({'status': 'CANCELADA'}).eq('id', reserva['id']).execute()
        user = supabase.table('users').select('rol').eq('id', reserva['user_id']).single().execute().data
        if user and user['rol'] == 'ABONADO':
            benefits.otorgar_credito(reserva['user_id'])
        else:
            # depositar_reserva(reserva['amount_paid'], user['email']) #pendiente_de_implementar
            pass


def cancelar_clase(class_id: str, cancel_reason: str):
    try:
        if not cancel_reason or not cancel_reason.strip():
            raise HTTPException(status_code=400, detail='La razón de cancelación es obligatoria.')

        # Cambia el status a CANCELADA (valida existencia y estado internamente)
        cancel_class(class_id)

        # Registrar motivo en tabla cancellations (no en classes, que no tiene esa columna)
        _registrar_cancelacion(class_id, cancel_reason.strip(), tipo='MANUAL')

        # Cancelar reservas y aplicar beneficios
        _cancelar_reservas_de_clase(class_id)

        return {'message': 'Clase cancelada exitosamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la clase: {str(e)}')


def cancelacion_automatica(class_id: str):
    try:
        if class_id is None:
            raise HTTPException(status_code=400, detail='El ID de la clase es obligatorio para la cancelación automática.')

        clase = (
            supabase.table('classes')
            .select('professor_id, start_time')
            .eq('id', class_id)
            .single()
            .execute()
        ).data
        if not clase:
            raise HTTPException(status_code=404, detail='La clase seleccionada no existe.')

        start_time = datetime.fromisoformat(clase['start_time'])
        ahora = datetime.now(timezone.utc)
        diferencia_horas = (start_time - ahora).total_seconds() / 3600

        if clase['professor_id'] is None and diferencia_horas <= 12:
            cancel_class(class_id)
            _registrar_cancelacion(
                class_id,
                cancel_reason='Cancelación automática por falta de profesor.',
                tipo='AUTOMATICA'
            )
            _cancelar_reservas_de_clase(class_id)
            return {'message': 'Clase cancelada automáticamente por falta de profesor.'}

        return {'message': 'No se cumplen las condiciones para cancelar la clase automáticamente.'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al cancelar la clase: {str(e)}')
