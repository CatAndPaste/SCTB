from aiogram import Router, types
from aiogram.filters import CommandStart

from aiogram.methods import SetMyDescription

from app.models import User
from app.utils.locale import load_locale
from app.utils.db import get_session

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            user = User(id=message.from_user.id, name=message.from_user.full_name)
            session.add(user)
            await session.commit()
            # Set bot description
            await message.bot(SetMyDescription(description="Scalping Crypto Trading Bot\n\nAvailable in russian and english language.\n\nДоступен на русском и английском языках.\n\nАвтоматическая торговля парой USDT/BTC: настройка торгового цикла, создание ордеров, просмотр баланса, статистики и текущих ордеров и многое другое…"))
            # Ask for language
            await message.answer("Choose your language / Выберите язык", reply_markup=language_keyboard())
        else:
            locale = load_locale(user.language or 'en')
            await message.answer(locale["welcome_back"])

def language_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="Русский язык", callback_data="lang_ru")],
        [types.InlineKeyboardButton(text="English", callback_data="lang_en")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def register_start_handlers(dp):
    dp.include_router(router)
