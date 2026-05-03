from aiogram.filters.callback_data import CallbackData


class CryptoSelection(CallbackData, prefix="crypto_select"):
    action: str  # 'sell' или 'buy'
    crypto: str  # 'BTC', 'TRX', 'USDT'


class RubInputSwitch(CallbackData, prefix="rub_switch"):
    action: str
    crypto: str


class CryptoInputSwitch(CallbackData, prefix="crypto_switch"):
    action: str
    crypto: str


class OrdersPage(CallbackData, prefix="orders_page"):
    page: int  # номер страницы (начиная с 0)


class AdminOrderAction(CallbackData, prefix="ao"):
    action: str   # 'confirm' или 'reject'
    order_id: int
    user_id: int


class CancelOrder(CallbackData, prefix="cancel_order"):
    order_id: int


class AdminManageAction(CallbackData, prefix="adm_manage"):
    action: str   # 'remove'
    user_id: int


class UserBlockAction(CallbackData, prefix="user_block"):
    action: str   # 'block' | 'unblock'
    user_id: int
