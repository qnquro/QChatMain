import os

from aiogram.filters import Command
from dotenv import load_dotenv
from aiogram import Router, Bot, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,StatesGroup
from database.database_logic import Database

load_dotenv()

password = os.getenv("PASSWORD")
host = os.getenv("HOST")
user = os.getenv("USER")
db_name = os.getenv("DB_NAME")

router_start = Router()

dp = Database(host=host, user=user, password=password, dbname=db_name)

class ThemeState(StatesGroup):
    mainTheme = State()
    subTheme = State()

async def mainMessage(chat_id : int, bot: Bot):
    kb = [
        [types.KeyboardButton(text="Вопрос дня"),
         types.KeyboardButton(text="Темы")]
    ]
    keyboard =types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Выберите")
    return await bot.send_message(chat_id,
    """Привет, это бот с анонимными вопросами
                              
    Ты можешь задать вопрос, ответить на вопросы других анонимно или как ты пожелаешь
                              
    Нажми на кнопку ниже, чтобы увидеть темы вопросов или увидеть вопрос дня""",
    reply_markup=keyboard
    )


@router_start.message(Command("start"))
async def startMessage(message: types.Message):
    await mainMessage(message.chat.id, message.bot)

@router_start.message(F.text.lower()=="темы")
async def showThemes(message: types.Message, state: FSMContext):

