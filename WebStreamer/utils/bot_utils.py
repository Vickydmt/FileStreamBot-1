# This file is a part of TG-FileStreamBot

from __future__ import annotations
from pyrogram.errors import UserNotParticipant
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.file_id import FileId, FileType, PHOTO_TYPES
from WebStreamer.utils.Translation import Language
from WebStreamer.utils.database import Database
from WebStreamer.utils.file_properties import get_media_file_size, get_name
from WebStreamer.utils.human_readable import humanbytes
from WebStreamer.vars import Var

db = Database(Var.DATABASE_URL, Var.SESSION_NAME)

async def is_user_joined(message:Message,lang) -> bool:
    try:
        user = await message._client.get_chat_member(Var.UPDATES_CHANNEL, message.chat.id)
        if user.status == "BANNED":
            await message.reply_text(
                text=lang.BAN_TEXT.format(Var.OWNER_ID),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return False
    except UserNotParticipant:
        await message.reply_text(
            text="<i>Jᴏɪɴ ᴍʏ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ 🔐</i>",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("Jᴏɪɴ ɴᴏᴡ 🔓", url=f"https://t.me/{Var.UPDATES_CHANNEL}")
                    ]]
            ),
            parse_mode=ParseMode.HTML
        )
        return False
    except Exception:
        await message.reply_text(
            text=f"<i>Sᴏᴍᴇᴛʜɪɴɢ ᴡʀᴏɴɢ ᴄᴏɴᴛᴀᴄᴛ ᴍʏ ᴅᴇᴠᴇʟᴏᴘᴇʀ</i> <b><a href='https://t.me/{Var.UPDATES_CHANNEL}'>[ ᴄʟɪᴄᴋ ʜᴇʀᴇ ]</a></b>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True)
        return False
    return True

# Generate Text, Stream Link, reply_markup
async def gen_link(m: Message, _id, name: list) -> tuple[InlineKeyboardMarkup, str]:
    """Generate Text for Stream Link, Reply Text and reply_markup"""
    lang = Language(m)
    file_name = get_name(m)
    file_size = humanbytes(get_media_file_size(m))
    import random
    available_urls = Var.MULTI_URLS if Var.MULTI_URLS else ([Var.WORKER_URL] if Var.WORKER_URL else [Var.URL])
    base_url = random.choice(available_urls)
    if not base_url.endswith("/"):
        base_url += "/"
    page_link = f"{base_url}watch/{_id}"
    stream_link = f"{base_url}dl/{_id}"
    stream_text=lang.STREAM_MSG_TEXT.format(file_name, file_size, stream_link, page_link, name[0], name[1])
    reply_markup=InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🖥STREAM", url=page_link), InlineKeyboardButton("Dᴏᴡɴʟᴏᴀᴅ 📥", url=stream_link)]
            ]
        )

    return reply_markup, stream_text

async def is_user_banned(message, lang) -> bool:
    if await db.is_user_banned(message.from_user.id):
        await message.reply_text(
            text=lang.BAN_TEXT.format(Var.OWNER_ID),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return True
    return False

async def is_user_exist(message: Message):
    if not bool(await db.get_user(message.from_user.id)):
        await db.add_user(message.from_user.id)
        await message._client.send_message(
            Var.BIN_CHANNEL,
            f"**Nᴇᴡ Usᴇʀ Jᴏɪɴᴇᴅ:** \n\n__Mʏ Nᴇᴡ Fʀɪᴇɴᴅ__ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) __Sᴛᴀʀᴛᴇᴅ Yᴏᴜʀ Bᴏᴛ !!__"
        )

async def is_user_accepted_tos(message: Message) -> bool:
    user=await db.get_user(message.from_user.id)
    if not ("agreed_to_tos" in user) or not user["agreed_to_tos"]:
        await message.reply(f"Hi {message.from_user.mention},\nplease read and accept the Terms of Service to continue using the bot")
        await message.reply_text(
            Var.TOS,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("I accept the TOS", callback_data=f"accepttos_{message.from_user.id}")]])
            )
        return False
    return True

async def is_allowed(message: Message):
    if Var.ALLOWED_USERS and not ((str(message.from_user.id) in Var.ALLOWED_USERS) or (message.from_user.username in Var.ALLOWED_USERS)):
        await message.reply("You are not in the allowed list of users who can use me.", quote=True)
        return False
    return True

async def validate_user(message: Message, lang=None) -> bool:
    if not await is_allowed(message):
        print("User validation failed: Not in allowed users")
        return False
    await is_user_exist(message)
    if Var.TOS:
        if not await is_user_accepted_tos(message):
            print("User validation failed: TOS not accepted")
            return False

    if not lang:
        lang = Language(message)
    if await is_user_banned(message, lang):
        print("User validation failed: User banned")
        return False
    if Var.FORCE_UPDATES_CHANNEL:
        if not await is_user_joined(message,lang):
            print("User validation failed: User not in update channel")
            return False
    return True

def file_format(file_id: str | FileId) -> str:
    if isinstance(file_id, str):
        file_id=FileId.decode(file_id)
    if file_id.file_type in PHOTO_TYPES:
        return "Photo"
    elif file_id.file_type == FileType.VOICE:
        return "Voice"
    elif file_id.file_type in (FileType.VIDEO, FileType.ANIMATION, FileType.VIDEO_NOTE):
        return "Video"
    elif file_id.file_type == FileType.DOCUMENT:
        return "Document"
    elif file_id.file_type == FileType.STICKER:
        return "Sticker"
    elif file_id.file_type == FileType.AUDIO:
        return "Audio"
    else:
        return "Unknown"
