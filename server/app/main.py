# server/app/main.py
#
# Entry point: `uvicorn app.main:app` (from the server/ directory).

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .database import Base, engine
from . import models  # noqa: F401 — registers models with Base before create_all
from .api import router as api_router
from .admin_panel import router as admin_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AutoGarideh Licensing Server")

app.include_router(api_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return RedirectResponse("/admin")


@app.get("/health")
def health():
    return {"status": "ok"}
