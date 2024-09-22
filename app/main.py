import asyncio
import os
import ssl
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiohttp import web
from dotenv import load_dotenv
from sqlalchemy import select

from app.models import User
from app.utils.db import get_session
from app.utils.locale import load_locale
from handlers import register_handlers
from middlewares import setup_middlewares
from config import DOMAIN_NAME
from utils.commands import set_default_commands, set_user_commands
from database import create_db_and_tables

try:
    import uvloop
except ImportError:
    uvloop = None
    pass

load_dotenv()

API_TOKEN = os.getenv('BOT_TOKEN')
BOT_WEBHOOK_BASE_URL = os.getenv('BOT_WEBHOOK_BASE_URL')
BOT_WEBHOOK_PATH = os.getenv('BOT_WEBHOOK_PATH')

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 8443

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)

# Регистрация обработчиков
register_handlers(dp)

# Настройка middlewares
setup_middlewares(dp)

async def subscription_checker():
    while True:
        async with get_session() as session:
            now = datetime.utcnow()
            users = await session.execute(select(User).where(User.subscription == True))
            users = users.scalars().all()
            for user in users:
                if user.subscription_expires:
                    days_remaining = (user.subscription_expires - now).days
                    locale = load_locale(user.language)
                    if days_remaining == 5:
                        await bot.send_message(user.id, locale["subscription_expiring"].format(days=5))
                    elif days_remaining <= 0:
                        user.subscription = False
                        await session.commit()
                        await bot.send_message(user.id, locale["subscription_expired"])
                        # Reset commands
                        await set_user_commands(bot, user.id, user.language, user.subscription)
        await asyncio.sleep(86400)  # Проверяем раз в сутки


async def on_startup(app):
    await bot.delete_webhook()
    await bot.set_webhook(f"{BOT_WEBHOOK_BASE_URL}{BOT_WEBHOOK_PATH}")
    await create_db_and_tables()
    await set_default_commands(bot)
    asyncio.create_task(subscription_checker())

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=BOT_WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(f'/etc/letsencrypt/live/{DOMAIN_NAME}/fullchain.pem',
                            f'/etc/letsencrypt/live/{DOMAIN_NAME}/privkey.pem')

if __name__ == '__main__':
    if uvloop:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT, ssl_context=ssl_context)
