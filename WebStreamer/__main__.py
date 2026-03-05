# This file is a part of TG-FileStreamBot

import sys
import random
import asyncio
import traceback
import logging
import logging.handlers as handlers
from aiohttp import web
from pyrogram import idle
from WebStreamer.bot import StreamBot
from WebStreamer.server import web_server
from WebStreamer.utils import ping_server
from WebStreamer.bot.clients import initialize_clients
from .vars import Var


logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(stream=sys.stdout),
              handlers.RotatingFileHandler("streambot.log", mode="a", maxBytes=104857600, backupCount=2, encoding="utf-8")],)

logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

server = web.AppRunner(web_server())

#if sys.version_info[1] > 9:
#    loop = asyncio.new_event_loop()
#    asyncio.set_event_loop(loop)
#else:
loop = asyncio.get_event_loop()

async def start_services():
    if Var.HF_TOKEN:
        try:
            from huggingface_hub import login
            login(token=Var.HF_TOKEN)
            print("------------------ Logged into Hugging Face ------------------")
        except Exception as e:
            print(f"Failed to login to Hugging Face: {e}")
    print()
    if Var.SECONDARY:
        print("------------------ Starting as Secondary Server ------------------")
    else:
        print("------------------- Starting as Primary Server -------------------")
    print()
    print("-------------------- Initializing Telegram Bot --------------------")
    # Staggered login to avoid FloodWait across multiple spaces
    delay = random.randint(5, 20)
    print(f"Waiting {delay} seconds before login to avoid FloodWait...")
    await asyncio.sleep(delay)
    await StreamBot.start()
    bot_info = await StreamBot.get_me()
    StreamBot.id = bot_info.id
    StreamBot.username = bot_info.username
    StreamBot.fname=bot_info.first_name
    print("------------------------------ DONE ------------------------------")
    print()
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    if Var.KEEP_ALIVE:
        print("------------------ Starting Keep Alive Service ------------------")
        print()
        asyncio.create_task(ping_server())
    print()
    print("--------------------- Initializing Web Server ---------------------")
    await server.setup()
    await web.TCPSite(server, Var.BIND_ADDRESS, Var.PORT).start()
    print("------------------------------ DONE ------------------------------")
    print()
    print("------------------------- Service Started -------------------------")
    print(f"                        bot =>> {bot_info.first_name}")
    if bot_info.dc_id:
        print(f"                        DC ID =>> {str(bot_info.dc_id)}")
    print(f" URL =>> {Var.URL}")
    print("------------------------------------------------------------------")
    await idle()

async def cleanup():
    await server.cleanup()
    try:
        await StreamBot.stop()
    except Exception:
        pass

if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logging.error(traceback.format_exc())
    finally:
        loop.run_until_complete(cleanup())
        loop.stop()
        print("------------------------ Stopped Services ------------------------")
