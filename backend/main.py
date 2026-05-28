import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.payments import routerPayments

from routes.auth import router as auth_router
from routes.staff import routerStaff as staff_router
from routes.user import routerUser as user_router
from routes.classes import router as classes_router
from routes.cancellations import router as cancellations_router
<<<<<<< HEAD
from routes.mp_webhook import routerMPWebhook
=======
>>>>>>> origin/feature/reserve_mangment
from routes.reservations import router as reservations_router

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

@app.get("/")
def health_check():
    return {"status": "ok", "message": "RehabilitAR API corriendo"}


