from aiogram import Router, types, F
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.formatting import Text

from app.models import User
from app.utils.locale import load_locale
from app.utils.db import get_session
from app.utils.commands import set_user_commands

router = Router()

class Registration(StatesGroup):
    waiting_for_api_key = State()

@router.callback_query(Text(startswith='lang_'))
async def language_callback(callback_query: types.CallbackQuery, state: FSMContext):
    language_code = callback_query.data.split('_')[1]
    async with get_session() as session:
        user = await session.get(User, callback_query.from_user.id)
        if user:
            user.language = language_code
            await session.commit()
            locale = load_locale(language_code)
            await callback_query.message.answer(locale["enter_api_key"], reply_markup=ReplyKeyboardRemove())
            await state.set_state(Registration.waiting_for_api_key)
    await callback_query.answer()

@router.message(Registration.waiting_for_api_key)
async def api_key_received(message: types.Message, state: FSMContext):
    api_key = message.text.strip()
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        locale = load_locale(user.language)
        if len(api_key) != 12:
            await message.answer(locale["api_key_invalid"])
            return
        # Placeholder for API key validation
        user.api_key = api_key  # Should be encrypted
        await session.commit()
        await message.answer(locale["api_key_saved"])
        await message.answer(locale["subscription_prompt"], reply_markup=subscription_keyboard(user.language))
        await state.clear()
        # Set default commands for user
        await set_user_commands(message.bot, user.id, user.language, user.subscription)

def subscription_keyboard(language_code):
    locale = load_locale(language_code)
    buttons = [
        [types.InlineKeyboardButton(text=locale["subscription_option_service"], callback_data="subscribe_service")],
        [types.InlineKeyboardButton(text=locale["subscription_option_stars"], callback_data="subscribe_stars")],
        [types.InlineKeyboardButton(text=locale["subscription_option_direct"], callback_data="subscribe_direct")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def register_registration_handlers(dp):
    dp.include_router(router)
