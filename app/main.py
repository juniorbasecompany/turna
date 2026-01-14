from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Turna API (Fase 1)")
app.include_router(router)
