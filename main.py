import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

if __name__ == "__main__":
    dp.start_polling(bot)