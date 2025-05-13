import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import handlers

load_dotenv()

TOKEN = os.getenv("TOKEN")

bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(handlers.start.router_start)
dp.include_router(handlers.handler_themes.router_themes)


if __name__ == "__main__":
    dp.start_polling(bot)