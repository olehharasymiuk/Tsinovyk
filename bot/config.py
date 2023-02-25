import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from dotenv import load_dotenv
from bot.data import data_path
from bot.database.models.goods import init_db
from bot.handlers import register_all_handlers
from bot.middlewares import setup_middleware
from bot.misc.scheduler import scheduler
from bot.utils.set_commands import set_bot_commands

load_dotenv(dotenv_path=f'{data_path}/.env')
APP_URL = 'https://tsinovyk.herokuapp.com/'


DEPLOY = os.environ.get('DEPLOY', False)

BOT_TOKEN = str(os.environ.get('BOT_TOKEN'))
ADMIN_ID = os.getenv('ADMIN_ID')

bot = Bot(BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot, storage=MemoryStorage())

WEBHOOK_PORT = 8080
WEBHOOK_HOST = ''
WEBHOOK_PATH = BOT_TOKEN


async def on_startup(_):

    if DEPLOY:
        await bot.set_webhook(url=APP_URL + BOT_TOKEN)

    init_db()
    scheduler()
    setup_middleware(dp)
    register_all_handlers(dp)

    await set_bot_commands(dp)


async def on_shutdown(_):

    await bot.delete_webhook()


def main():

    if DEPLOY:
        executor.set_webhook(
            dispatcher=dp,
            webhook_path='',
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
        )

    else:
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
