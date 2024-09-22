from aiogram import BaseMiddleware
from aiogram.types import Message
from datetime import datetime
from app.utils.db import get_session
from app.models import User
from aiogram.methods import SendMessage

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            if event.text.startswith('/'):
                command = event.text.split()[0][1:]
                allowed_commands = ['start', 'help', 'subscription']
                async with get_session() as session:
                    user = await session.get(User, event.from_user.id)
                    if not user:
                        await event.answer("Please select your language first.")
                        return
                    data['user'] = user
                    if not user.subscription or (user.subscription_expires and user.subscription_expires <= datetime.utcnow()):
                        if command not in allowed_commands:
                            await event.answer("This section is available only with a subscription. Please purchase a subscription via /subscription.")
                            return
        return await handler(event, data)
