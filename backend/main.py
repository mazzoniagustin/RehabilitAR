import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.payments import routerPayments
from services.cancellations import classes_cancellation_service
from services import automatic_notifications_service

from routes.auth import router as auth_router
from routes.staff import routerStaff as staff_router
from routes.user import routerUser as user_router
from routes.classes import router as classes_router
from routes.cancellations import router as cancellations_router
from routes.mp_webhook import routerMPWebhook
from routes.reservations import router as reservations_router
from routes.attendance import routerAttendance
from routes.notifications import router as notification_router
from routes.audit import routerAudit

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RehabilitAR API",
    version="1.0.0"
)

# En producción, setear ALLOWED_ORIGINS como variable de entorno con los dominios
# separados por coma. Ej: ALLOWED_ORIGINS="https://rehabilitar.com,https://www.rehabilitar.com"
# Si no está definida, se usan los orígenes locales de desarrollo.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if _raw_origins.strip():
    allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.mount(
    "/frontend",
    StaticFiles(directory=os.path.join(BASE_DIR, "frontend"), html=True),
    name="frontend"
)

app.include_router(auth_router)
app.include_router(staff_router)
app.include_router(user_router) 
app.include_router(classes_router)
app.include_router(routerPayments)
app.include_router(cancellations_router)
app.include_router(routerMPWebhook)
app.include_router(reservations_router)
app.include_router(routerAttendance)
app.include_router(notification_router)
app.include_router(routerAudit)


async def _automatic_no_professor_cancellation_loop():
    interval_seconds = int(os.getenv("NO_PROFESSOR_CANCELLATION_INTERVAL_SECONDS", "900"))
    while True:
        try:
            result = classes_cancellation_service.cancelar_clases_sin_profesor()
            if result.get("cancelled_count", 0) or result.get("errors"):
                logger.info("Cancelación automática sin profesor: %s", result)
        except Exception as exc:
            logger.exception("Error en cancelación automática sin profesor: %s", exc)
        await asyncio.sleep(interval_seconds)


async def _attendance_reminder_loop():
    interval_seconds = int(os.getenv("ATTENDANCE_REMINDER_INTERVAL_SECONDS", "900"))
    while True:
        try:
            result = automatic_notifications_service.enviar_recordatorios_asistencia()
            if result.get("sent_count", 0) or result.get("errors"):
                logger.info("Recordatorios de asistencia: %s", result)
        except Exception as exc:
            logger.exception("Error en recordatorios de asistencia: %s", exc)
        await asyncio.sleep(interval_seconds)


async def _no_professor_notification_loop():
    interval_seconds = int(os.getenv("NO_PROFESSOR_NOTIFICATION_INTERVAL_SECONDS", "900"))
    while True:
        try:
            result = automatic_notifications_service.avisar_profesores_clases_sin_profesor()
            if result.get("sent_count", 0) or result.get("errors"):
                logger.info("Avisos de clases sin profesor: %s", result)
        except Exception as exc:
            logger.exception("Error en avisos de clases sin profesor: %s", exc)
        await asyncio.sleep(interval_seconds)


async def _debt_reminder_loop():
    interval_seconds = int(os.getenv("DEBT_REMINDER_INTERVAL_SECONDS", "900"))
    while True:
        try:
            result = automatic_notifications_service.enviar_recordatorios_deuda_pendiente()
            if result.get("sent_count", 0) or result.get("errors"):
                logger.info("Recordatorios de deuda pendiente: %s", result)
        except Exception as exc:
            logger.exception("Error en recordatorios de deuda pendiente: %s", exc)
        await asyncio.sleep(interval_seconds)


async def _subscription_due_soon_loop():
    interval_seconds = int(os.getenv("SUBSCRIPTION_DUE_SOON_INTERVAL_SECONDS", "900"))
    while True:
        try:
            result = automatic_notifications_service.notificar_cercania_vencimiento_suscripcion()
            if result.get("sent_count", 0) or result.get("errors"):
                logger.info("Avisos de cercanía de vencimiento de suscripción: %s", result)
        except Exception as exc:
            logger.exception("Error en avisos de cercanía de vencimiento de suscripción: %s", exc)
        await asyncio.sleep(interval_seconds)


async def _subscription_payment_expired_loop():
    interval_seconds = int(os.getenv("SUBSCRIPTION_PAYMENT_EXPIRED_INTERVAL_SECONDS", "900"))
    while True:
        try:
            result = automatic_notifications_service.notificar_vencimiento_plazo_pago_deuda()
            if result.get("sent_count", 0) or result.get("errors"):
                logger.info("Avisos de vencimiento de plazo de pago: %s", result)
        except Exception as exc:
            logger.exception("Error en avisos de vencimiento de plazo de pago: %s", exc)
        await asyncio.sleep(interval_seconds)


@app.on_event("startup")
async def start_automatic_jobs():
    app.state.no_professor_cancellation_task = asyncio.create_task(
        _automatic_no_professor_cancellation_loop()
    )
    app.state.attendance_reminder_task = asyncio.create_task(
        _attendance_reminder_loop()
    )
    app.state.no_professor_notification_task = asyncio.create_task(
        _no_professor_notification_loop()
    )
    app.state.debt_reminder_task = asyncio.create_task(
        _debt_reminder_loop()
    )
    app.state.subscription_due_soon_task = asyncio.create_task(
        _subscription_due_soon_loop()
    )
    app.state.subscription_payment_expired_task = asyncio.create_task(
        _subscription_payment_expired_loop()
    )


@app.on_event("shutdown")
async def stop_automatic_jobs():
    tasks = [
        getattr(app.state, "no_professor_cancellation_task", None),
        getattr(app.state, "attendance_reminder_task", None),
        getattr(app.state, "no_professor_notification_task", None),
        getattr(app.state, "debt_reminder_task", None),
        getattr(app.state, "subscription_due_soon_task", None),
        getattr(app.state, "subscription_payment_expired_task", None),
    ]
    for task in tasks:
        if not task:
            continue
        task.cancel()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "RehabilitAR API corriendo"}
