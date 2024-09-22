from aiogram import Router, types
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from datetime import datetime, timedelta

from aiogram.utils.formatting import Text

from app.models import User
from app.utils.locale import load_locale
from app.utils.db import get_session
from app.utils.commands import set_user_commands

router = Router()

@router.message(Command('subscription'))
async def cmd_subscription(message: types.Message):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        locale = load_locale(user.language)
        if user.subscription and user.subscription_expires > datetime.utcnow():
            remaining_days = (user.subscription_expires - datetime.utcnow()).days
            await message.answer(locale["subscription_active"].format(days=remaining_days), reply_markup=subscription_keyboard(user.language, renew=True))
        else:
            await message.answer(locale["subscription_inactive"], reply_markup=subscription_keyboard(user.language))

def subscription_keyboard(language_code, renew=False):
    locale = load_locale(language_code)
    buttons = [
        [types.InlineKeyboardButton(text=locale["subscription_option_service"], callback_data="subscribe_service")],
        [types.InlineKeyboardButton(text=locale["subscription_option_stars"], callback_data="subscribe_stars")],
        [types.InlineKeyboardButton(text=locale["subscription_option_direct"], callback_data="subscribe_direct")],
        [types.InlineKeyboardButton(text=locale["subscription_option_test"], callback_data="subscribe_test")],  # Новая опция
    ]
    if renew:
        buttons.append([types.InlineKeyboardButton(text=locale["subscription_option_extend"], callback_data="extend_subscription")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data.startswith('subscribe_'))
async def subscription_callback(callback_query: types.CallbackQuery):
    action = callback_query.data.split('_')[1]
    async with get_session() as session:
        user = await session.get(User, callback_query.from_user.id)
        locale = load_locale(user.language)
        if action == 'service':
            await callback_query.message.answer("This feature will be implemented later.")
        elif action == 'stars':
            await callback_query.message.answer("Purchase with Telegram Stars is not yet implemented.")
        elif action == 'direct':
            await callback_query.message.answer("Please contact the administrator for direct payment.")
        elif action == 'test':
            # Предоставляем тестовую подписку
            user.subscription = True
            user.subscription_expires = datetime.utcnow() + timedelta(days=7)  # Тестовая подписка на 7 дней
            await session.commit()
            remaining_days = (user.subscription_expires - datetime.utcnow()).days
            await callback_query.message.answer(f"You have received a test subscription! Days remaining: {remaining_days}")
            # Обновляем команды пользователя
            await set_user_commands(callback_query.bot, user.id, user.language, user.subscription)
        elif action == 'extend':
            user.subscription_expires += timedelta(days=30)
            await session.commit()
            remaining_days = (user.subscription_expires - datetime.utcnow()).days
            await callback_query.message.answer(locale["subscription_active"].format(days=remaining_days))
            user.subscription = True
            await set_user_commands(callback_query.bot, user.id, user.language, user.subscription)
    await callback_query.answer()

def register_subscription_handlers(dp):
    dp.include_router(router)
