import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from handlers import start, handler_themes

load_dotenv()

TOKEN = os.getenv("TOKEN")

bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(start.router_start )
dp.include_router(handler_themes.router_themes)


if __name__ == "__main__":
    dp.run_polling(bot)