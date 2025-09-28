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
# Proxy routers will be imported from handlers.crypto.proxy (module creates them)
proxy_private_router = None
proxy_group_router = None


def _register_crypto():
    # Импортируем модули внутри функции, чтобы избежать циклического импорта
    from handlers import main as main_handlers, crypto
    # Универсальные сообщения/состояния
    crypto_router.message.register(crypto.process_amount_input, TransactionStates.waiting_for_crypto_amount)
    crypto_router.message.register(crypto.process_amount_input, TransactionStates.waiting_for_rub_amount)
    # message handlers for operator replies are registered via decorators in handlers/crypto.py
    crypto_router.message.register(crypto.phone_input_handler, TransactionStates.waiting_for_phone)
    # message handlers for operator replies are registered via decorators in handlers/crypto.py

    # Callback handlers - меню
    crypto_router.callback_query.register(main_handlers.start_handler, F.data == 'main_menu')
    crypto_router.callback_query.register(main_handlers.profile_handler, F.data == 'profile')
    crypto_router.callback_query.register(crypto.sell_handler, F.data == 'sell')
    crypto_router.callback_query.register(crypto.buy_handler, F.data == 'buy')

    # Generic selection filters
    crypto_router.callback_query.register(crypto.select_crypto_handler, CryptoSelection.filter())
    crypto_router.callback_query.register(crypto.switch_to_rub_input_handler, RubInputSwitch.filter())
    crypto_router.callback_query.register(crypto.select_crypto_handler, CryptoInputSwitch.filter())

    # Transaction callbacks: payment and operator-reply handlers are registered in module decorators
    crypto_router.callback_query.register(crypto.cancel_transaction_handler, F.data == 'cancel_transaction')
    crypto_router.callback_query.register(crypto.cancel_order_handler, F.data == 'cancel_order')


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


def _register_main():
    # Импорт внутри функции, чтобы избежать циклического импорта
    from handlers import main as main_handlers
    main_router.message.register(main_handlers.start_handler, Command(commands=['start']))
    main_router.message.register(main_handlers.profile_handler, Command(commands=['profile']))
    main_router.message.register(main_handlers.promo_command_handler, Command(commands=['promo']))

    # Promo states
    from handlers.admin import PromoStates
    from handlers.main import UserPromoStates
    from handlers import admin
    main_router.message.register(admin.process_new_promo_code, PromoStates.waiting_for_promo_code)
    main_router.message.register(main_handlers.process_user_promo_code, UserPromoStates.waiting_for_code)


def register_all_routers():
    """Выполняет регистрацию во внутренних Router'ах.

    После вызова этой функции можно подключать роутеры к Dispatcher:
        dp.include_router(main_router)
        dp.include_router(crypto_router)
        dp.include_router(admin_router)
    """
    # Регистрация main/crypto/admin
    _register_main()
    _register_crypto()
    _register_admin()
    # Импортируем proxy модуль, чтобы декораторы в нём выполнились и роутеры были созданы
    try:
        from handlers.crypto import proxy as proxy_handlers
        # Экспортируем ссылки для main.py
        global proxy_private_router, proxy_group_router
        proxy_private_router = proxy_handlers.private_message_router
        proxy_group_router = proxy_handlers.group_message_router
    except Exception:
        # Если импорт не удался — он будет поднят при попытке include_router в main
        proxy_private_router = None
        proxy_group_router = None

