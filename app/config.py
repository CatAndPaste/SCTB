import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://user:password@localhost/dbname')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
BOT_WEBHOOK_BASE_URL = os.getenv('BOT_WEBHOOK_BASE_URL')
BOT_WEBHOOK_PATH = os.getenv('BOT_WEBHOOK_PATH')

SUBSCRIPTION_PRICE = 1
