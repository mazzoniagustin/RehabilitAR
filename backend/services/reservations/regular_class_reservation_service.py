from database import supabase
from fastapi import HTTPException

def reservar_clase_fija(user_id: str, class_id: str):
    try:
        # Normalizar a str por si llegan como objetos UUID desde Pydantic
        user_id = str(user_id)
        class_id = str(class_id)

        clase_response = supabase.table('classes').select('*').eq('id', class_id).single().execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail='Clase no encontrada.')
        clase = clase_response.data

        if not clase['is_scheduled']:
            raise HTTPException(status_code=400, detail='Esta clase no es fija.')

        user_response = supabase.table('users').select('*').eq('id', user_id).single().execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        user = user_response.data

        if user['account_status'] != 'ACTIVA':
            raise HTTPException(status_code=403, detail='Reserva fallida, no se encuentra habilitado para tomar la clase.')

        # Verificar que no tenga ya una reserva confirmada para esta clase
        existing = (
            supabase.table('reservations')
            .select('id')
            .eq('user_id', user_id)
            .eq('class_id', class_id)
            .eq('status', 'CONFIRMADA')
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=400, detail='Ya tenés una reserva confirmada para esta clase.')

        prioridad = 'ABONADO' if user['rol'] == 'ABONADO' else 'NO_ABONADO'

        if clase['current_capacity'] < clase['max_capacity']:
            # Incrementar con condición en el WHERE para evitar race conditions
            update_response = (
                supabase.table('classes')
                .update({'current_capacity': clase['current_capacity'] + 1})
                .eq('id', class_id)
                .eq('current_capacity', clase['current_capacity'])  # condición anti-race
                .lt('current_capacity', clase['max_capacity'])
                .select()  # necesario para que Supabase devuelva las filas afectadas
                .execute()
            )

            if not update_response.data:
                # La clase se llenó entre el check y el update — ir a waitlist
                return _agregar_a_waitlist(user_id, class_id, prioridad)

            supabase.table('reservations').insert({
                'user_id': user_id,
                'class_id': class_id,
                'status': 'CONFIRMADA'
            }).execute()
            return {'message': 'Inscripción exitosa.'}

        # Clase llena: agregar a la lista de espera con prioridad FIFO por tipo
        return _agregar_a_waitlist(user_id, class_id, prioridad)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error al realizar la reserva: {str(e)}')


def _agregar_a_waitlist(user_id: str, class_id: str, prioridad: str):
    """
    Agrega al usuario a la lista de espera respetando prioridad FIFO:
    - ABONADO tiene prioridad sobre NO_ABONADO.
    - Dentro del mismo nivel de prioridad, se respeta el orden de llegada.
    """
    ya_en_lista = (
        supabase.table('waitlist')
        .select('id')
        .eq('user_id', user_id)
        .eq('class_id', class_id)
        .execute()
    )
    if ya_en_lista.data:
        raise HTTPException(status_code=400, detail='Ya estás en la lista de espera para esta clase.')

    waitlist_response = (
        supabase.table('waitlist')
        .select('position, priority, priority_order')
        .eq('class_id', class_id)
        .order('position', desc=True)
        .execute()
    )
    entradas = waitlist_response.data or []

    nueva_posicion = (entradas[0]['position'] + 1) if entradas else 1

    mismo_nivel = [e for e in entradas if e['priority'] == prioridad]
    nuevo_priority_order = (
        max(e['priority_order'] for e in mismo_nivel) + 1
    ) if mismo_nivel else 1

    supabase.table('waitlist').insert({
        'user_id': user_id,
        'class_id': class_id,
        'position': nueva_posicion,
        'priority': prioridad,
        'priority_order': nuevo_priority_order,
    }).execute()

    return {'message': 'La clase se encuentra llena. Fuiste agregado a la lista de espera.'}
