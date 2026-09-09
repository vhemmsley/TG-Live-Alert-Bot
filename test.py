"""Connection test - run: python test.py"""
import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_RAW = os.getenv("TARGET_CHAT_ID")


async def main() -> None:
    async with Bot(TOKEN) as bot:
        me = await bot.get_me()
        print("Bot username:", me.username)

        try:
            chat_id = int(CHAT_ID_RAW)
        except (TypeError, ValueError):
            print("TARGET_CHAT_ID is not a valid number:", CHAT_ID_RAW)
            return

        try:
            chat = await bot.get_chat(chat_id)
            print("Chat found ->",
                  "title:", chat.title,
                  "| type:", chat.type,
                  "| id:", chat.id)
        except Exception as exc:
            print("FAIL getChat:", exc)
            print("-> The bot cannot see this chat. "
                  "Wrong ID, or the bot is NOT admin "
                  "in that channel.")
            return

        try:
            await bot.send_message(chat_id, "Connection test OK")
            print("Test message sent successfully.")
        except Exception as exc:
            print("FAIL send_message:", exc)
            print("-> Bot sees the chat but cannot post. "
                  "Check admin rights (post permission).")


asyncio.run(main())
