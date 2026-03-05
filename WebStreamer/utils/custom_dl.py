# This file is a part of TG-FileStreamBot

import asyncio
import logging
from typing import AsyncGenerator, Dict, Union
from pyrogram import Client, utils, raw
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from WebStreamer.bot import work_loads
from WebStreamer.vars import Var
from .file_properties import get_file_ids


class ByteStreamer:
    def __init__(self, client: Client):
        """A custom class that holds the cache of a specific client and class functions.
        attributes:
            client: the client that the cache is for.
            cached_file_ids: a dict of cached file IDs.
            cached_file_properties: a dict of cached file properties.
        
        functions:
            generate_file_properties: returns the properties for a media of a specific message contained in Tuple.
            generate_media_session: returns the media session for the DC that contains the media file.
            yield_file: yield a file from telegram servers for streaming.
            
        This is a modified version of the <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/telegram/utils/custom_download.py>
        Thanks to Eyaadh <https://github.com/eyaadh>
        """
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.cached_file_ids: Dict[str, FileId] = {}
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, db_id: str, multi_clients) -> FileId:
        """
        Returns the properties of a media of a specific message in a FIleId class.
        if the properties are cached, then it'll return the cached results.
        or it'll generate the properties from the Message ID and cache them.
        """
        if not db_id in self.cached_file_ids:
            logging.debug("Before Calling generate_file_properties")
            await self.generate_file_properties(db_id, multi_clients)
            logging.debug("Cached file properties for file with ID %s", db_id)
        return self.cached_file_ids[db_id]

    async def generate_file_properties(self, db_id: str, multi_clients) -> FileId:
        """
        Generates the properties of a media file on a specific message.
        returns ths properties in a FIleId class.
        """
        logging.debug("Before calling get_file_ids")
        file_id = await get_file_ids(self.client, db_id, multi_clients)
        logging.debug("Generated file ID and Unique ID for file with ID %s", db_id)
        self.cached_file_ids[db_id] = file_id
        logging.debug("Cached media file with ID %s", db_id)
        return self.cached_file_ids[db_id]

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        """
        Generates the media session for the DC that contains the media file.
        This is required for getting the bytes from Telegram servers.
        """

        return await client.get_session(file_id.dc_id, is_media=True)


    @staticmethod
    async def get_location(file_id: FileId) -> Union[raw.types.InputPhotoFileLocation,
                                                     raw.types.InputDocumentFileLocation,
                                                     raw.types.InputPeerPhotoFileLocation,]:
        """
        Returns the file location for the media file.
        """
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                photo_id=file_id.media_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG
            )
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        return location

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ) -> AsyncGenerator[bytes, None]:
        client = self.client
        work_loads[index] += 1
        logging.debug("Starting to yield file with client %s.", index)

        # Cache the media session for this specific DC
        if not hasattr(self, "cached_session"):
            self.cached_session = None
        
        if not self.cached_session:
            logging.debug("Initializing media session for DC %s...", file_id.dc_id)
            self.cached_session = await self.generate_media_session(client, file_id)

        location = await self.get_location(file_id)

        async def fetch(off):
            for i in range(3):
                try:
                    r = await asyncio.wait_for(
                        self.cached_session.invoke(raw.functions.upload.GetFile(location=location, offset=off, limit=chunk_size)),
                        timeout=15
                    )
                    if isinstance(r, raw.types.upload.File):
                        return r.bytes
                except Exception as e:
                    logging.error(f"Chunk fetch error (try {i+1}): {e}")
                await asyncio.sleep(1)
            return b""

        try:
            # 24 is the stable maximum for a single Telegram account
            concurrency = min(Var.DOWNLOAD_CONCURRENCY, 24) 
            tasks = {}
            next_part = 1
            fetch_part = 1
            current_offset = offset

            while next_part <= part_count:
                while fetch_part <= part_count and len(tasks) < concurrency:
                    tasks[fetch_part] = asyncio.create_task(fetch(current_offset))
                    fetch_part += 1
                    current_offset += chunk_size
                
                chunk = await tasks.pop(next_part)
                if not chunk:
                    logging.error("Failed to fetch part %s, skipping...", next_part)
                
                if part_count == 1:
                    yield chunk[first_part_cut:last_part_cut]
                elif next_part == 1:
                    yield chunk[first_part_cut:]
                elif next_part == part_count:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk
                
                next_part += 1

        except Exception as e:
            logging.error(f"Streaming error: {e}")
        finally:
            logging.debug("Finished yielding file with %s parts.", next_part - 1)
            work_loads[index] -= 1


    async def clean_cache(self) -> None:
        """
        function to clean the cache to reduce memory usage
        """
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
            logging.debug("Cleaned the cache")
