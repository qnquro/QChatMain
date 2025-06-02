import os

from aiogram.filters import Command
from dotenv import load_dotenv
from aiogram import Router, Bot, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.database_logic import Database
import random
import logging

logger = logging.getLogger(__name__)

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
    replying = State()
    choose_anonim = State()
    confirming_reply = State()
    creating_discussion = State()


async def mainMessage(chat_id: int, bot: Bot):
    kb = [
        [types.KeyboardButton(text="Рандомный вопрос"),
         types.KeyboardButton(text="Темы")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Выберите")
    return await bot.send_message(chat_id,
                                  """Привет, это бот с анонимными вопросами
                                  
                                  Ты можешь задать вопрос, ответить на вопросы других анонимно или как ты пожелаешь
                                  
                                  Нажми на кнопку ниже, чтобы увидеть темы вопросов или увидеть вопрос дня""",
                                  reply_markup=keyboard)


@router_start.message(Command("start"))
async def startMessage(message: types.Message):
    await mainMessage(message.chat.id, message.bot)


@router_start.message(F.text.lower() == "темы")
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


@router_start.message(F.text.lower() == "рандомный вопрос")
async def rand_question(message: types.Message, state: FSMContext):
    from handlers.handler_themes import show_discussion
    temp_msg = await message.answer("Ищу случайный вопрос...", reply_markup=types.ReplyKeyboardRemove())
    await temp_msg.delete()

    root_ids = db.get_root_discussion_ids()
    if not root_ids:
        await message.answer("❌ Нет доступных вопросов")
        return
    random_disc_id = random.choice(root_ids)
    theme_info = db.get_theme_info_for_discussion(random_disc_id)
    if not theme_info:
        await message.answer("❌ Не удалось найти информацию по теме")
        return
    await state.update_data(
        current_discussion=random_disc_id,
        main_theme_id=theme_info[1],
        subtheme_id=theme_info[0]
    )
    await show_discussion(message, state, random_disc_id)
    await state.set_state(ThemeState.discussion)
