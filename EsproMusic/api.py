# EsproMusic/api.py
import time
from fastapi import FastAPI, Query
from typing import Optional, Union

from EsproMusic import app as tg_app, LOGGER
from EsproMusic.misc import _boot_

api = FastAPI(title="EsproMusic API", version="1.0.0")

@api.get("/")
async def root():
    return {
        "status": "ok",
        "service": "EsproMusic",
        "uptime_sec": round(time.time() - _boot_, 2),
    }

@api.get("/health")
async def health():
    return {"ok": True}

# Simple utility endpoint: send a text message via bot
@api.post("/send_message")
async def send_message(
    chat_id: Union[int, str] = Query(..., description="User/Chat/Channel ID or @username"),
    text: str = Query(..., description="Message text (HTML enabled)")
):
    # Pyrogram client (tg_app) is already started in __main__.py
    await tg_app.send_message(chat_id=chat_id, text=text)
    return {"sent": True, "chat_id": chat_id}
