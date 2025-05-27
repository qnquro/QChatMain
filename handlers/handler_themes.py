from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from aiogram.types import CallbackQuery
from start import mainMessage
from start import ThemeState as Theme
from start import db

router_themes = Router()


# Функция для получения автора в формате HTML
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

    discussions = db.get_discussions(subtheme_id)
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


# Получение ответов и взаимодействие(просмотр, ответить)
@router_themes.callback_query(F.data.startswith("discussion_"), Theme.discussion)
async def handle_discussion(callback: types.CallbackQuery, state: FSMContext, discussion_id=None):
    if discussion_id is None:
        discussion_id = int(callback.data.split("_")[1])
    discussion = db.get_discussion(discussion_id)
    replies = db.get_replies(discussion_id)

    if not discussion:
        await callback.message.answer("Обсуждение не найдено")
        return

    text = f"Обсуждение: {discussion.get('content')}"
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


@router_themes.callback_query(F.data.startswith("reply_"), Theme.discussion)
async def starting_reply(callback: CallbackQuery, state: FSMContext):
    discussion_id = int(callback.data.split("_")[1])
    await state.update_data(reply_to=discussion_id)
    await callback.message.answer("Введите ваш ответ (текст, фото или видео):")
    await state.set_state(Theme.replying)
    await callback.answer()


@router_themes.message(Theme.replying)
async def recieve_reply(message: types.Message, state: FSMContext):
    content_type = 'text'
    content = None
    media_id = None
    if message.text:
        content = message.text
    elif message.photo:
        content_type = 'photo'
        media_id = message.photo[-1].file_id
        content = message.caption or ''
    elif message.video:
        content_type = 'video'
        media_id = message.video.file_id
        content = message.caption or ''
    else:
        await message.reply("Неподдерживаемый тип контента. Пожалуйста, отправьте текст, фото или видео.")
        return
    await state.update_data(content=content, media_id=media_id, content_type=content_type)
    kb = [
        [types.InlineKeyboardButton(text="Анонимно", callback_data='anonim')],
        [types.InlineKeyboardButton(text="С юзернеймом", callback_data='with_username')]
    ]
    await message.answer("Выберите как опубликовать ответ", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(Theme.choose_anonim)


@router_themes.callback_query(F.data.in_(['anonim', 'with_username']), Theme.choose_anonim)
async def choose_anonim(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    content = data.get('content')
    content_type = data.get('content_type')
    if callback.data == 'anonim':
        author = "Аноним"
        user_id = None
    else:
        author = callback.from_user.username or callback.from_user.first_name
        user_id = callback.from_user.id
    preview = content if content_type == 'text' else "Медиа"
    text = f"Ваш ответ: {preview}\nАвтор: {author}\n\nПодтвердите отправку:"
    kb = [
        [types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_reply")],
        [types.InlineKeyboardButton(text="Отменить", callback_data="cancel_reply")]
    ]
    await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.update_data(author=author, user_id=user_id)
    await state.set_state(Theme.confirming_reply)


@router_themes.callback_query(F.data == "confirm_reply", Theme.confirming_reply)
async def save_reply(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    discussion_id = data['reply_to']
    content = data['content']
    content_type = data['content_type']
    media_id = data.get('media_id')
    author = data['author']
    user_id = data['user_id']

    db.add_reply(discussion_id, author, content, content_type, media_id, user_id)
    await callback.message.answer("Ваш ответ сохранён.")
    await state.clear()
    await handle_discussion(callback, state, discussion_id)
    await callback.answer()


@router_themes.callback_query(F.data == "cancel_reply", Theme.confirming_reply)
async def cancel_reply(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправка ответа отменена.")
    await state.clear()
    await handle_discussion(callback, state)
    await callback.answer()


@router_themes.callback_query(F.data.startswith("create_discussion_"), Theme.discussion)
async def start_create_discussion(callback: types.CallbackQuery, state: FSMContext):
    subtheme_id = int(callback.data.split("_")[2])
    await state.update_data(subtheme_id=subtheme_id)
    await callback.message.answer("Введите текст вашего обсуждения:")
    await state.set_state(Theme.creating_discussion)
    await callback.answer()


@router_themes.message(Theme.creating_discussion)
async def receive_discussion(message: types.Message, state: FSMContext):
    content = message.text
    await state.update_data(content=content)

    kb = [
        [types.InlineKeyboardButton(text="Анонимно", callback_data="anonymous_create")],
        [types.InlineKeyboardButton(text="С юзернеймом", callback_data="with_username_create")]
    ]
    await message.answer("Выберите, как опубликовать обсуждение:",
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))


@router_themes.callback_query(F.data.in_(["anonymous_create", "with_username_create"]), Theme.creating_discussion)
async def save_discussion(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    subtheme_id = data['subtheme_id']
    content = data['content']
    author = "Аноним" if callback.data == "anonymous_create" else callback.from_user.username or callback.from_user.first_name

    db.add_discussion(subtheme_id, author, content)
    await callback.message.answer("Ваше обсуждение создано.")
    await state.clear()
    await handle_subthemes(callback, state, subtheme_id)
    await callback.answer()

@router_themes.callback_query(F.data == "back_to_main_menu")
async def handle_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_themes = db.get_main_themes()

    kb = []
    for theme_id, title in main_themes:
        kb.append([types.InlineKeyboardButton(
            text=title,
            callback_data=f"theme_{theme_id}"
        )])

    await callback.message.edit_text(
        "Выберите основную тему:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(Theme.mainTheme)
    await callback.answer()


@router_themes.callback_query(F.data == "main_menu")
async def handle_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await mainMessage(callback.message.chat.id, callback.bot)
    await callback.answer()
