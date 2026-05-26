import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.payments import routerPayments

app = FastAPI(
    title="RehabilitAR API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
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

from routes.auth import router as auth_router
from routes.staff import routerStaff as staff_router
from routes.user import routerUser as user_router

app.include_router(auth_router)
app.include_router(staff_router)
app.include_router(user_router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "RehabilitAR API corriendo"}

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(staff_router)
app.include_router(routerPayments)