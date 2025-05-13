from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from start import ThemeState as Theme
from start import db
router_themes = Router()


@router_themes.callback_query(F.data.startswith("theme_"), StateFilter(Theme.mainTheme, Theme.discussion))
async def handle_main_theme(callback: types.CallbackQuery, state: FSMContext):
    theme_id= int(callback.data.split("_")[1])
    await state.update_data(main_theme_id=theme_id)

    subthemes=db.get_subthemes(theme_id)
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


@router_themes.callback_query(F.data.startswith("subtheme_"), StateFilter(Theme.subTheme, Theme.discussion))
async def handle_subthemes(callback:types.CallbackQuery, state : FSMContext, subtheme_id = None):
    if subtheme_id is None:
        subtheme_id = int(callback.data.split("_")[1])
    await state.update_data(subtheme_id=subtheme_id)
    data = await state.get_data()
    main_theme_id = data["main_theme_id"]

    discussions = db.get_discussion(subtheme_id)
    kb = []
    for disc_id, author, content in discussions:
        if len(content)>50:
            preview = content[55]+"..."
        else:
            preview=content
        button=f"{author}: {preview}"
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
