from fastapi import APIRouter

from app.services import store
from .notes import helper

router = APIRouter(prefix="/api/v1")


@router.get("/messages/{message_id}")
def read_message(message_id: int):
    return store.save(helper())


@router.post("/messages")
async def send():
    return store.save(helper())


@router.api_route("/bulk", methods=["PUT", "PATCH"])
def bulk():
    ...
