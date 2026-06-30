import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.payments import routerPayments
from services.cancellations import classes_cancellation_service

from routes.auth import router as auth_router
from routes.staff import routerStaff as staff_router
from routes.user import routerUser as user_router
from routes.classes import router as classes_router
from routes.cancellations import router as cancellations_router
from routes.mp_webhook import routerMPWebhook
from routes.reservations import router as reservations_router
from routes.attendance import routerAttendance
from routes.notifications import router as notification_router

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


@app.on_event("startup")
async def start_automatic_jobs():
    app.state.no_professor_cancellation_task = asyncio.create_task(
        _automatic_no_professor_cancellation_loop()
    )


@app.on_event("shutdown")
async def stop_automatic_jobs():
    task = getattr(app.state, "no_professor_cancellation_task", None)
    if task:
        task.cancel()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "RehabilitAR API corriendo"}
