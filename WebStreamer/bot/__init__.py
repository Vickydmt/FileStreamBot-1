# This file is a part of TG-FileStreamBot


from pyrogram import Client
from ..vars import Var

if Var.SECONDARY:
    PLUGINS=None
    NO_UPDATES=True
else:
    PLUGINS={"root": "WebStreamer.bot.plugins"}
    NO_UPDATES=None

StreamBot = Client(
    name="WebStreamer",
    api_id=Var.API_ID,
    api_hash=Var.API_HASH,
    workdir="WebStreamer",
    plugins=PLUGINS,
    bot_token=Var.BOT_TOKEN,
    sleep_threshold=Var.SLEEP_THRESHOLD,
    workers=Var.WORKERS,
    no_updates=NO_UPDATES
)

print(f"Debug: StreamBot initialized with plugins: {PLUGINS} / {StreamBot.plugins}")

multi_clients = {}
work_loads = {}
