from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from start import ThemeState as theme
from start import db
router_themes = Router()


@router_themes.callback_query(F.data.startswith("theme_"), StateFilter(theme.mainTheme, theme.discussion))
async def handle_main_theme(callback: types.CallbackQuery, state: FSMContext):
    theme_id= int(callback.data.split("_")[1])
    await state.update_data(main_theme_id=theme_id)

    subthemes=db.get_subthemes(theme_id)
    kb = []
