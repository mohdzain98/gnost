from fastapi import FastAPI

import app.services as services_pkg  # noqa: F401
from app.api.v1 import chat, notes
from app.config import settings

app = FastAPI(title=settings.name)
app.include_router(chat.router, prefix="/chat")
app.include_router(notes.router)


@app.get("/health")
async def health():
    return {"ok": True}
