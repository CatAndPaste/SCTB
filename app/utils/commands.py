from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

commands_ru = [
    BotCommand(command="/autobuy", description="🤖 Автопокупка"),
    BotCommand(command="/buy", description="💸 Покупка"),
    BotCommand(command="/orders", description="🧾 Открытые ордеры"),
    BotCommand(command="/params", description="⚙️ Параметры"),
    BotCommand(command="/stop", description="🛑 Остановить автопокупку"),
    BotCommand(command="/stats", description="ℹ️ Статистика"),
    BotCommand(command="/balance", description="💰 Баланс"),
    BotCommand(command="/price", description="📈 Текущая цена"),
    BotCommand(command="/subscription", description="✨ Подписка"),
    BotCommand(command="/help", description="📖 Помощь"),
]

commands_en = [
    BotCommand(command="/autobuy", description="🤖 Autobuy"),
    BotCommand(command="/buy", description="💸 Buy"),
    BotCommand(command="/orders", description="🧾 Open orders"),
    BotCommand(command="/params", description="⚙️ Options"),
    BotCommand(command="/stop", description="🛑 Stop autobuying"),
    BotCommand(command="/stats", description="ℹ️ Stats"),
    BotCommand(command="/balance", description="💰 Balance"),
    BotCommand(command="/price", description="📈 Current Price"),
    BotCommand(command="/subscription", description="✨ Subscription"),
    BotCommand(command="/help", description="📖 Help"),
]

default_commands_ru = [
    BotCommand(command="/start", description="Начать работу с ботом"),
    BotCommand(command="/help", description="📖 Помощь"),
    BotCommand(command="/subscription", description="✨ Подписка"),
]

default_commands_en = [
    BotCommand(command="/start", description="Start the bot"),
    BotCommand(command="/help", description="📖 Help"),
    BotCommand(command="/subscription", description="✨ Subscription"),
]

async def set_default_commands(bot):
    """
    Устанавливает команды по умолчанию для всех пользователей.
    """
    await bot.set_my_commands(default_commands_en, scope=BotCommandScopeDefault(), language_code='en')
    await bot.set_my_commands(default_commands_ru, scope=BotCommandScopeDefault(), language_code='ru')

async def set_user_commands(bot, user_id, language_code, has_subscription):
    """
    Устанавливает команды для конкретного пользователя в зависимости от наличия подписки.
    """
    print(user_id)
    print(has_subscription)
    if has_subscription:
        commands = commands_ru if language_code == 'ru' else commands_en
    else:
        commands = default_commands_ru if language_code == 'ru' else default_commands_en
    scope = BotCommandScopeChat(chat_id=user_id)
    await bot.set_my_commands(commands=commands, scope=scope, language_code=language_code)
