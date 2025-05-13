from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from start import ThemeState as Theme
from start import db

router_themes = Router()


#Функция для получения автора в формате HTML
def format_author(author, user_id):
    if user_id:
        return f"<a href='tg://user?id={user_id}'>{author}</a>"
    else:
        return author


# Выбор подтемы. Из callback'а берётся значение темы и переходит в состояние subtheme
@router_themes.callback_query(F.data.startswith("theme_"), StateFilter(Theme.mainTheme, Theme.discussion))
async def handle_main_theme(callback: types.CallbackQuery, state: FSMContext):
    theme_id = int(callback.data.split("_")[1])
    await state.update_data(main_theme_id=theme_id)

    subthemes = db.get_subthemes(theme_id)
    kb = []
    for sub_id, title in subthemes:
        kb.append(
            [types.InlineKeyboardButton(text=title, callback_data=f"subtheme_{sub_id}")]
        )
    kb.append([types.InlineKeyboardButton(text="Назад", callback_data="back_to_main_menu")])

    await callback.message.edit_text("Выберите подтему",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
                                     )

    await state.set_state(Theme.subTheme)
    await callback.answer()


# Выбор дискуссии в теме. Из callback'а берётся id сабтемы и выбираются все доступные дискуссии в ней(только показ, только выбор дискуссии)
@router_themes.callback_query(F.data.startswith("subtheme_"), StateFilter(Theme.subTheme, Theme.discussion))
async def handle_subthemes(callback: types.CallbackQuery, state: FSMContext, subtheme_id=None):
    if subtheme_id is None:
        subtheme_id = int(callback.data.split("_")[1])
    await state.update_data(subtheme_id=subtheme_id)
    data = await state.get_data()
    main_theme_id = data["main_theme_id"]

    discussions = db.get_discussion(subtheme_id)
    kb = []
    for disc_id, author, content in discussions:
        if len(content) > 50:
            preview = content[55] + "..."
        else:
            preview = content
        button = f"{author}: {preview}"
        kb.append(
            [types.InlineKeyboardButton(text=button, callback_data=f"discussion_{disc_id}")]
        )

    kb.append([
        types.InlineKeyboardButton(text="Создать обсуждение", callback_data=f"create_discussion_{subtheme_id}"),
        types.InlineKeyboardButton(text="Назад", callback_data=f"theme_{main_theme_id}"),
        types.InlineKeyboardButton(text="Главное меню", callback_data="main_menu")
    ])
    await callback.message.edit_text(
        "Доступные обсуждения", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(Theme.discussion)
    await callback.answer()


#Получение ответов и взаимодействие(просмотр, ответить)
@router_themes.callback_query(F.data.startswith("discussion_"), Theme.discussion)
async def handle_discussion(callback: types.CallbackQuery, state: FSMContext, discussion_id=None):
    if discussion_id is None:
        discussion_id = int(callback.data.split("_")[1])
    discussion = db.get_discussion(discussion_id)
    replies = db.get_replies(discussion_id)

    if not discussion:
        await callback.answer("Обсуждение не найдено")
        return

    text = f"Обсуждение: {discussion}"
    data = await state.get_data()
    subtheme_id = data.get("subtheme_id")
    kb = [
        [types.KeyboardButton(text="Ответить"),
         types.KeyboardButton(text="Назад")]
    ]
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )
    bot = callback.bot
    chat_id = callback.message.chat.id
    for reply in replies:
        author_text = format_author(reply['author'], reply['user_id'])
        if reply['content_type'] == 'text':
            message_text = f"{author_text}: {reply['content']}"
            await bot.send_message(chat_id, message_text, parse_mode="HTML")
        elif reply['content_type'] == 'photo':
            caption = f"{author_text}: {reply['content']}"
            await bot.send_photo(chat_id, reply['media_id'], caption=caption, parse_mode="HTML")
        elif reply['content_type'] == 'video':
            caption = f"{author_text}: {reply['content']}"
            await bot.send_video(chat_id, reply['media_id'], caption=caption, parse_mode="HTML")
    await callback.answer()


