from fastapi import APIRouter

from ...models import Note
from app.config import settings

router = APIRouter()


@router.get("/notes")
def helper():
    return Note(), settings


@router.websocket("/ws/notes")
async def stream(websocket):
    ...
