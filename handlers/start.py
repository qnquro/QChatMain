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

db = Database(host=host, user=user, password=password, dbname=db_name)

class ThemeState(StatesGroup):
    mainTheme = State()
    subTheme = State()
    discussion = State()

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
    message_id = await message.answer("...", reply_markup=types.ReplyKeyboardRemove())
    await message_id.delete()
    themes = db.get_main_themes()
    kb = []
    for theme_id, title in themes:
        kb.append(
            [types.InlineKeyboardButton(text=title, callback_data=f"theme_{theme_id}")]
        )
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    msg = await message.answer("Выберите основную тему", reply_markup=keyboard)
    await state.update_data(main_message_id=msg.message_id)
    await state.set_state(ThemeState.mainTheme)

