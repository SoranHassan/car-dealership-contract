# server/main.py
import os
import json
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

from .database import Base, engine, SessionLocal
from .models import Contract

Base.metadata.create_all(bind=engine)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_ROOT = os.path.join(BASE_DIR, "contracts_storage")
os.makedirs(STORAGE_ROOT, exist_ok=True)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


@app.post("/api/contracts/upload")
async def upload_contract(
    contract_number: str = Form(...),
    buyer_id: str = Form(...),
    created_at: str = Form(...),
    file: UploadFile = File(...)
):
    dt = datetime.fromisoformat(created_at)
    year = dt.strftime("%Y")
    month = dt.strftime("%m")

    dir_path = os.path.join(STORAGE_ROOT, year, month)
    os.makedirs(dir_path, exist_ok=True)

    filename = f"{contract_number}_{buyer_id}_{dt.strftime('%Y%m%d%H%M%S')}.docx"
    file_path = os.path.join(dir_path, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    db = SessionLocal()
    try:
        c = Contract(
            contract_number=str(contract_number),
            buyer_id=str(buyer_id),
            file_path=file_path,
            created_at=dt
        )
        db.add(c)
        db.commit()
        db.refresh(c)
    finally:
        db.close()

    return {"status": "ok", "id": c.id}


@app.get("/api/config")
def get_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {"sync_mode": "immediate", "sync_interval_seconds": 300}
    return cfg