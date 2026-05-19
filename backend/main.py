from fastapi import FastAPI

from routes.classes import router as classes_router

app = FastAPI()

app.include_router(classes_router)