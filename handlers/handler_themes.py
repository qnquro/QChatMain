from typing import Union
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from aiogram.types import CallbackQuery, ReplyKeyboardRemove
from handlers.start import mainMessage
from handlers.start import ThemeState as Theme
from handlers.start import db

router_themes = Router()


# Функция для получения автора в формате HTML
def format_author(author, user_id):
    if user_id:
        return f"<a href='tg://user?id={user_id}'>{author}</a>"
    else:
        return author


# Функция для получения тем(слишком большая и важная)
async def show_discussion(event: Union[CallbackQuery, types.Message], state: FSMContext, discussion_id: int,
                          page: int = 0):
    # Получение данных из БД
    discussion = db.get_discussion(discussion_id)
    replies = db.get_replies(discussion_id)

    if not discussion:
        await event.answer("Обсуждение не найдено")
        return

    await state.update_data(current_discussion=discussion_id, page=page)

    total_replies = len(replies)
    max_page = max(0, (total_replies + 9) // 10 - 1)
    start = page * 10
    end = min(start + 10, total_replies)
    replies_pg = replies[start:end]

    text = f"Обсуждение: {discussion.get('content')}"
    kb = [
        [types.KeyboardButton(text="Ответить"),
         types.KeyboardButton(text="Назад")],
        []
    ]

    if page > 0:
        kb[1].append(types.KeyboardButton(text="◀️ Предыдущая"))
    if page < max_page:
        kb[1].append(types.KeyboardButton(text="▶️ Следующая"))

    # Определение параметров чата
    if isinstance(event, CallbackQuery):
        chat_id = event.message.chat.id
        bot = event.bot
        message_func = event.message.answer
    else:
        chat_id = event.chat.id
        bot = event.bot
        message_func = event.answer

    await message_func(
        text,
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )

    data = await state.get_data()
    old_messages = data.get('messages', [])
    for msg_id in old_messages:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass

    # Отправка ответов
    new_messages = []
    for reply in replies_pg:
        author_text = format_author(reply['author'], reply['user_id'])
        sent_msg = None
        if reply['content_type'] == 'text':
            message_text = f"{author_text}: {reply['content']}"
            sent_msg = await bot.send_message(chat_id, message_text, parse_mode="HTML")

        elif reply['content_type'] in ['photo', 'video', 'animation']:
            caption = f"{author_text}: {reply['content']}"
            if reply['content_type'] == 'photo':
                sent_msg = await bot.send_photo(chat_id, reply['media_id'], caption=caption, parse_mode="HTML")
            elif reply['content_type'] == 'video':
                sent_msg = await bot.send_video(chat_id, reply['media_id'], caption=caption, parse_mode="HTML")
            elif reply['content_type'] == 'animation':
                sent_msg = await bot.send_animation(chat_id, reply['media_id'], caption=caption, parse_mode="HTML")

        elif reply['content_type'] in ['document', 'audio']:
            caption = f"{author_text}: {reply['content']}"
            if reply['content_type'] == 'document':
                sent_msg = await bot.send_document(
                    chat_id,
                    reply['media_id'],
                    caption=caption,
                    parse_mode="HTML",
                    file_name=reply.get('file_name')
                )
            elif reply['content_type'] == 'audio':
                sent_msg = await bot.send_audio(
                    chat_id,
                    reply['media_id'],
                    caption=caption,
                    parse_mode="HTML",
                    title=reply.get('file_name')
                )
        elif reply['content_type'] in ['voice', 'video_note', 'sticker']:
            if reply['content']:
                await bot.send_message(chat_id, f"{author_text}: {reply['content']}", parse_mode="HTML")
            else:
                await bot.send_message(chat_id, author_text, parse_mode="HTML")
            if reply['content_type'] == 'voice':
                sent_msg = await bot.send_voice(chat_id, reply['media_id'])
            elif reply['content_type'] == 'video_note':
                sent_msg = await bot.send_video_note(chat_id, reply['media_id'])
            elif reply['content_type'] == 'sticker':
                sent_msg = await bot.send_sticker(chat_id, reply['media_id'])
        if sent_msg:
            new_messages.append(sent_msg.message_id)

    await state.update_data(messages=new_messages, max_page=max_page)

    if isinstance(event, CallbackQuery):
        await event.answer()


# Выбор подтемы. Из callback'а берётся значение темы и переходит в состояние subtheme
@router_themes.callback_query(F.data.startswith("theme_"), StateFilter(Theme.mainTheme, Theme.discussion))
async def handle_main_theme(callback: types.CallbackQuery, state: FSMContext):
    try:
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
    except:
        print("callback is none")
        data = await state.get_data()
        main_theme_id = data.get("main_theme_id")
        theme_id = main_theme_id
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
        await state.update_data(main_theme_id=None)
        await state.set_state(Theme.subTheme)
        await callback.answer()


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


@router_themes.callback_query(F.data.startswith("discussion_"), StateFilter(Theme.discussion))
async def handle_discussion_callback(callback: CallbackQuery, state: FSMContext):
    discussion_id = int(callback.data.split("_")[1])
    await show_discussion(callback, state, discussion_id)


@router_themes.message(F.text.lower() == "◀️ предыдущая", StateFilter(Theme.discussion))
async def prev_page(message: types.Message, state: FSMContext):
    data = await state.get_data()
    page = data.get("page", 0)
    discussion_id = data.get("current_discussion")
    if discussion_id and page > 0:
        await show_discussion(message, state, discussion_id, page - 1)


@router_themes.message(F.text.lower() == "▶️ следующая", StateFilter(Theme.discussion))
async def next_page(message: types.Message, state: FSMContext):
    data = await state.get_data()
    page = data.get("page", 0)
    max_page = data.get("max_page", 0)
    discussion_id = data.get("current_discussion")
    if discussion_id and page < max_page:
        await show_discussion(message, state, discussion_id, page + 1)


@router_themes.message(F.text.lower() == "назад", StateFilter(Theme.discussion))
async def handle_back(message: types.Message, state: FSMContext):
    data = await state.get_data()
    subtheme_id = data.get("subtheme_id")
    main_theme_id = data.get("main_theme_id")

    if not subtheme_id:
        await message.answer("❌ Ошибка навигации", reply_markup=ReplyKeyboardRemove())
        return

    message_id = await message.answer("...", reply_markup=ReplyKeyboardRemove())
    await message_id.delete()
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
    await message.answer(
        "Доступные обсуждения", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(Theme.discussion)


@router_themes.message(F.text.lower() == "ответить")
async def starting_reply(message: types.Message, state: FSMContext):
    data = await state.get_data()
    discussion_id = data.get("current_discussion")

    if not discussion_id:
        await message.answer("❌ Сначала выберите обсуждение!")
        return

    await state.update_data(reply_to=discussion_id)
    await message.answer("Введите ваш ответ (текст, фото или видео):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Theme.replying)


@router_themes.message(Theme.replying)
async def recieve_reply(message: types.Message, state: FSMContext):
    content_type = 'text'
    content = None
    media_id = None
    file_name = None  # Добавим для хранения имени файла
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
    elif message.document:
        content_type = 'document'
        media_id = message.document.file_id
        file_name = message.document.file_name
        content = message.caption or ''
    elif message.audio:
        content_type = 'audio'
        media_id = message.audio.file_id
        file_name = message.audio.file_name
        content = message.caption or ''
    elif message.voice:
        content_type = 'voice'
        media_id = message.voice.file_id
        content = message.caption or ''
    elif message.video_note:
        content_type = 'video_note'
        media_id = message.video_note.file_id
        content = message.caption or ''
    elif message.sticker:
        content_type = 'sticker'
        media_id = message.sticker.file_id
        content = ''
    elif message.animation:
        content_type = 'animation'
        media_id = message.animation.file_id
        content = message.caption or ''
    else:
        await message.reply("Неподдерживаемый тип контента. Отправьте текст, файл или медиа.")
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
    await show_discussion(callback, state, discussion_id)
    await callback.answer()
    await state.set_state(Theme.discussion)


@router_themes.callback_query(F.data == "cancel_reply", Theme.confirming_reply)
async def cancel_reply(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправка ответа отменена.")
    await show_discussion(callback, state)
    await callback.answer()
    await state.set_state(Theme.discussion)


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
    await handle_subthemes(callback, state, subtheme_id)
    await callback.answer()


@router_themes.callback_query(F.data == "back_to_main_menu")
async def handle_back_to_main(callback: types.CallbackQuery, state: FSMContext):
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
