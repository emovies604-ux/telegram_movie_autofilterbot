import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant
from config import *
from db import add_file, search_files, file_count, get_file_by_id, files

logging.basicConfig(level=logging.INFO)
app = Client("autofilter-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

RESULTS_PER_PAGE = 10
PAGE_CALLBACK_PREFIX = "filespage"

async def is_user_admin(client, message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        return True
    if message.chat.type == "private":
        return False
    try:
        member = await client.get_chat_member(message.chat.id, user_id)
        return member.status in ["administrator", "creator"]
    except UserNotParticipant:
        return False
    except Exception:
        return False

async def auto_delete_message(message, delay=30):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

@app.on_message(
    filters.channel & filters.chat(FILES_CHANNEL_ID) & (filters.document | filters.video | filters.audio)
)
async def index_file(client, message):
    media = message.document or message.video or message.audio
    if not media:
        return
    media_type = ("document" if message.document else "video" if message.video else "audio")
    file_info = {
        "file_id": media.file_id,
        "file_name": media.file_name or "",
        "caption": message.caption or "",
        "message_id": message.id,
        "channel_id": message.chat.id,
        "file_type": media_type
    }
    add_file(file_info)
    await app.send_message(LOG_CHANNEL_ID, f"Indexed file: {file_info.get('file_name', '')}")

@app.on_message(
    (filters.private | filters.group)
    & filters.text
    & ~filters.command(["start", "help", "stats", "deletefile"])
)
async def handle_search(client, message):
    query = message.text
    if message.chat.type == "group":
        pm_button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📩 Start me", url=f"https://t.me/{app.me.username}?start=1")]]
        )
        reply_msg = await message.reply(
            "⚠️ Please start me in private chat to get movie files.", reply_markup=pm_button
        )
        await auto_delete_message(reply_msg)
        return

    if query.startswith(f"@{app.me.username}"):
        query = query.replace(f"@{app.me.username}", "").strip()
    if not query:
        return

    results = search_files(query)
    if not results:
        reply_msg = await message.reply("🚫 Not Found! This message will delete in 30 seconds.\nJoin SUPPORT CHANNEL: @billo_movies")
        await auto_delete_message(reply_msg)
        return

    warning_note = "ℹ️ This message will delete in 30 seconds. Please forward the file if you want to keep it.\nJoin SUPPORT CHANNEL: @billo_movies"

    if len(results) == 1:
        r = results[0]
        file_type = r.get("file_type", "document")
        send_msg = None
        if file_type == "document":
            send_msg = await message.reply_document(document=r["file_id"], caption=r["file_name"])
        elif file_type == "video":
            send_msg = await message.reply_video(video=r["file_id"], caption=r["file_name"])
        elif file_type == "audio":
            send_msg = await message.reply_audio(audio=r["file_id"], caption=r["file_name"])
        else:
            send_msg = await message.reply_document(document=r["file_id"], caption=r["file_name"])
        warning_msg = await message.reply(warning_note)
        await auto_delete_message(send_msg)
        await auto_delete_message(warning_msg)
    else:
        page = 1
        start = 0
        end = RESULTS_PER_PAGE
        chunk = results[start:end]

        def get_buttons(page, total, chunk):
            buttons = [
                [InlineKeyboardButton(f"{i+1+start}. {r['file_name'][:40]}", callback_data=f"sendfile|{str(r['_id'])}")]
                for i, r in enumerate(chunk)
            ]
            nav = []
            total_pages = (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
            if page > 1:
                nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{PAGE_CALLBACK_PREFIX}|{query}|{page-1}"))
            if page < total_pages:
                nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"{PAGE_CALLBACK_PREFIX}|{query}|{page+1}"))
            if nav:
                buttons.append(nav)
            return buttons

        buttons = get_buttons(page, len(results), chunk)
        reply_msg = await message.reply("JOIN SUPPORT CHANNEL: @billo_movies\n\nMultiple files found, select from below:\n\n" + warning_note, reply_markup=InlineKeyboardMarkup(buttons))
        await auto_delete_message(reply_msg)

@app.on_callback_query(filters.regex(r"^filespage\|"))
async def pagination_handler(client, callback_query):
    data = callback_query.data.split("|", 2)
    if len(data) < 3:
        return await callback_query.answer("Invalid callback.", show_alert=True)
    _, query, page = data
    page = int(page)
    results = search_files(query)
    start = (page-1) * RESULTS_PER_PAGE
    end = page * RESULTS_PER_PAGE
    chunk = results[start:end]

    def get_buttons(page, total, chunk):
        buttons = [
            [InlineKeyboardButton(f"{i+1+start}. {r['file_name'][:40]}", callback_data=f"sendfile|{str(r['_id'])}")]
            for i, r in enumerate(chunk)
        ]
        nav = []
        total_pages = (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        if page > 1:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{PAGE_CALLBACK_PREFIX}|{query}|{page-1}"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"{PAGE_CALLBACK_PREFIX}|{query}|{page+1}"))
        if nav:
            buttons.append(nav)
        return buttons

    buttons = get_buttons(page, len(results), chunk)
    warning_note = "ℹ️ This message will delete in 30 seconds. Please forward the file if you want to keep it.\nJoin SUPPORT CHANNEL: @billo_movies"
    msg_txt = "Multiple files found, select from below:\n\n" + warning_note
    await callback_query.message.edit_text(
        msg_txt,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await auto_delete_message(callback_query.message)
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^sendfile\|"))
async def send_file_handler(client, callback_query):
    doc_id = callback_query.data.split("|")[1]
    file_record = get_file_by_id(doc_id)
    if not file_record:
        await callback_query.answer("File not found.", show_alert=True)
        return

    file_id = file_record["file_id"]
    file_type = file_record.get("file_type", "document")
    send_msg = None
    if file_type == "document":
        send_msg = await callback_query.message.reply_document(document=file_id)
    elif file_type == "video":
        send_msg = await callback_query.message.reply_video(video=file_id)
    elif file_type == "audio":
        send_msg = await callback_query.message.reply_audio(audio=file_id)
    else:
        send_msg = await callback_query.message.reply_document(document=file_id)
    warning_msg = await callback_query.message.reply("ℹ️ This message will delete in 30 seconds. Please forward the file if you want to keep it.\nJoin SUPPORT CHANNEL: @billo_movies")
    await auto_delete_message(send_msg)
    await auto_delete_message(warning_msg)
    await callback_query.answer()

@app.on_message(filters.command("stats") & (filters.private | filters.group))
async def stats(client, message):
    if not await is_user_admin(client, message):
        return await message.reply("❌ You don't have permission to use this command.")
    count = file_count()
    await message.reply(f"Total indexed files: {count}")

@app.on_message(filters.command("deletefile") & filters.private)
async def delete_file(client, message):
    if not await is_user_admin(client, message):
        return await message.reply("❌ You don't have permission to use this command.")
    if len(message.command) < 2:
        return await message.reply("Usage: /deletefile <movie name>")
    name_to_delete = " ".join(message.command[1:]).strip()
    matched_files = search_files(name_to_delete)
    if not matched_files:
        return await message.reply(f"No indexed files found matching '{name_to_delete}'.")
    deleted_count = 0
    for file in matched_files:
        result = files.delete_one({"_id": file["_id"]})
        if result.deleted_count:
            deleted_count += 1
    await message.reply(f"Deleted {deleted_count} indexed file(s) matching '{name_to_delete}'.")

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "👋 Welcome! Send a movie name to search files.\n Join SUPPORT CHANNEL: @billo_movies"
    )

@app.on_message(filters.command("help"))
async def help_handler(client, message):
    await message.reply(
        "Send a movie name to search files. If available, files will be sent to you.\n Join SUPPORT CHANNEL: @billo_movies"
    )

if __name__ == "__main__":
    app.run()
