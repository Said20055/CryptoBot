from aiogram.filters.callback_data import CallbackData

class CryptoSelection(CallbackData, prefix="crypto_select"):
    action: str  # 'sell' или 'buy'
    crypto: str  # 'BTC', 'LTC', и т.д.

class RubInputSwitch(CallbackData, prefix="rub_switch"):
    action: str
    crypto: str

class CryptoInputSwitch(CallbackData, prefix="crypto_switch"):
    action: str
    crypto: str