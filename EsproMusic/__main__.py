# EsproMusic/__main__.py

import asyncio
import importlib
import os

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from EsproMusic import LOGGER, app, userbot
from EsproMusic.core.call import Loy
from EsproMusic.misc import sudo
from EsproMusic.plugins import ALL_MODULES
from EsproMusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

# --- FastAPI / Uvicorn bits ---
from EsproMusic.api import api as fastapi_app
import uvicorn

async def run_api():
    port = int(os.getenv("PORT", "8000"))   # Heroku provides $PORT
    server = uvicorn.Server(
        uvicorn.Config(
            app=fastapi_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
        )
    )
    await server.serve()
# -------------------------------


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant client variables not defined, exiting...")
        raise SystemExit(1)

    await sudo()

    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception:
        pass

    # Start main bot client
    await app.start()

    # Import all plugins
    for mod in ALL_MODULES:
        # NOTE: ensure dot between package and module
        importlib.import_module("EsproMusic.plugins." + mod)
    LOGGER("EsproMusic.plugins").info("Successfully Imported Modules...")

    # Start userbot + voice call client
    await userbot.start()
    await Loy.start()

    try:
        await Loy.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("EsproMusic").error(
            "Please turn on the videochat of your log group/channel.\n\nStopping Bot..."
        )
        raise SystemExit(1)
    except Exception:
        pass

    await Loy.decorators()
    LOGGER("EsproMusic").info(
        "EsproMusicBot Started Successfully \n\n Yaha App ko nahi aana hai aapni hf jo bhej sakte hai @Esprosupport "
    )

    # Run Pyrogram idle loop + FastAPI together
    await asyncio.gather(
        idle(),      # keeps the Pyrogram clients alive
        run_api(),   # serves FastAPI on $PORT
    )

    # On graceful shutdown:
    await app.stop()
    await userbot.stop()
    LOGGER("EsproMusic").info("Stopping Espro Music Bot...")


if __name__ == "__main__":
    asyncio.run(init())
