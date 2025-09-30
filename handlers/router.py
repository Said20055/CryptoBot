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



def _register_admin():
    # Импорт внутри функции, чтобы избежать циклического импорта
    from handlers import admin
    admin_router.message.register(admin.broadcast_message_handler, admin.BroadcastStates.waiting_for_message)
    from handlers.admin import AdminReplyStates
    admin_router.message.register(admin.admin_reply_message_handler, AdminReplyStates.waiting_for_reply_message)

    admin_router.callback_query.register(admin.cancel_broadcast_handler, F.data == 'cancel_broadcast')
    # admin_router.callback_query.register(admin.admin_reply_handler, F.data.startswith('admin_reply_'))
    admin_router.callback_query.register(admin.confirm_order_handler, F.data.startswith('confirm_order_'))
    admin_router.callback_query.register(admin.reject_order_handler, F.data.startswith('reject_order_'))


try:
    
    from .proxy import private_message_router, group_message_router
except ImportError:
    # Заглушка на случай, если файл proxy.py будет удален
    print("WARNING: proxy.py not found, proxy routers are not available.")
    private_message_router = Router()
    group_message_router = Router()


def register_all_routers():
 
    _register_admin()
    

