"""
handlers/router.py

Создаёт `Router`-объекты и регистрирует на них существующие функции-хендлеры.
Это даёт ту же модульность, но позволяет в будущем переключиться на декораторы
(@router.callback_query(...)) без больших правок.
"""
from aiogram import Router, F
from aiogram.filters import Command

from utils.states import TransactionStates
from utils.callbacks import CryptoSelection, RubInputSwitch, CryptoInputSwitch


# Router'ы по группам
main_router = Router()
crypto_router = Router()
admin_router = Router()


try:
    
    from .proxy import private_message_router, group_message_router
except ImportError:
    # Заглушка на случай, если файл proxy.py будет удален
    print("WARNING: proxy.py not found, proxy routers are not available.")
    private_message_router = Router()
    group_message_router = Router()


