# This file is a part of TG-FileStreamBot

import asyncio
import logging
from os import environ
from pyrogram import Client
from ..vars import Var
from . import multi_clients, work_loads, StreamBot


async def initialize_clients():
    all_tokens = dict(
        (c + 1, t)
        for c, (_, t) in enumerate(
            filter(
                lambda n: n[0].startswith("MULTI_TOKEN"), sorted(environ.items())
            )
        )
    )
    
    # Export session string from main bot to reuse for additional workers
    # This avoids auth.ImportBotAuthorization FloodWait
    main_bot_session = await StreamBot.export_session_string()

    if not all_tokens:
        print(f"No MULTI_TOKEN found, creating {Var.WORKERS} parallel workers with main session")
        for i in range(1, Var.WORKERS + 1):
            all_tokens[i] = main_bot_session

    multi_clients[0] = StreamBot
    work_loads[0] = 0

    async def start_client(client_id, token):
        try:
            if len(token) >= 100:
                session_string=token
                bot_token=None
                # print(f'Starting Client - {client_id} Using Session String')
            else:
                session_string=None
                bot_token=token
                print(f'Starting Client - {client_id} Using Bot Token')
            
            client = await Client(
                name=str(client_id),
                api_id=Var.API_ID,
                api_hash=Var.API_HASH,
                bot_token=bot_token,
                sleep_threshold=Var.SLEEP_THRESHOLD,
                no_updates=True,
                session_string=session_string,
                in_memory=True,
            ).start()
            client.id = (await client.get_me()).id
            work_loads[client_id] = 0
            return client_id, client
        except Exception:
            logging.error("Failed starting Client - {%s} Error:", client_id, exc_info=True)

    if all_tokens:
        clients = []
        for i, token in all_tokens.items():
            res = await start_client(i, token)
            if res:
                clients.append(res)
            await asyncio.sleep(1) # Small delay to avoid auth flood
        multi_clients.update(dict(clients))
    
    if len(multi_clients) != 1:
        Var.MULTI_CLIENT = True
        print(f"Multi-Client Mode Enabled with {len(multi_clients)} clients")
