import asyncio
import os
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def main():
    print(f"Testing with API_ID={API_ID}, BOT_TOKEN={BOT_TOKEN[:10]}...")
    clients = []
    for i in range(3):
        c = Client(f"test_{i}", api_id=int(API_ID), api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
        await c.start()
        print(f"Client {i} started, id={c.me.id}")
        clients.append(c)
    
    for c in clients:
        await c.stop()
        print("Stopped client")

asyncio.run(main())
