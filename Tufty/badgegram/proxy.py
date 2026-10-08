from fastapi import FastAPI
from telethon import TelegramClient

API_ID = 123456
API_HASH = "your_api_hash"

client = TelegramClient("badgeware", API_ID, API_HASH)
app = FastAPI()


@app.on_event("startup")
async def startup():
    await client.start()


@app.get("/api/chats")
async def chats():
    result = []

    async for dialog in client.iter_dialogs(limit=20):
        result.append({
            "id": dialog.id,
            "title": dialog.name,
            "unread": dialog.unread_count,
        })

    return result


@app.get("/api/chats/{chat_id}/messages")
async def messages(chat_id: int, limit: int = 20):
    result = []

    async for message in client.iter_messages(chat_id, limit=limit):
        if message.text:
            result.append(message.text)

    return result
