# config.py

"""
Конфигурация бота.

Этот модуль загружает все настройки из файла .env,
чтобы отделить конфигурацию от кода.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# --- Telegram Bot Settings ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Загружаем ID админов из строки, разделенной запятыми
admin_ids_str = os.getenv("ADMIN_CHAT_IDS")
# Преобразуем строку в список целых чисел, убирая лишние пробелы
ADMIN_CHAT_ID = [int(admin_id.strip()) for admin_id in admin_ids_str.split(',')] if admin_ids_str else []

SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID", 0))

# --- Crypto Wallets ---
# Загружаем адреса кошельков. Если переменная не найдена, используется пустая строка.
CRYPTO_WALLETS = {
    "BTC": os.getenv("WALLET_BTC", ""),
    "LTC": os.getenv("WALLET_LTC", ""),
    "TRX": os.getenv("WALLET_TRX", ""),
    "USDT": os.getenv("WALLET_USDT", ""),
}


# --- Financial Settings ---
# Загружаем числовые значения и преобразуем их в нужный тип (int, float)
# Указываем значения по умолчанию на случай, если они не заданы в .env
NETWORK_FEE_RUB = int(os.getenv("NETWORK_FEE_RUB", 290))
SERVICE_COMMISSION_PERCENT = float(os.getenv("SERVICE_COMMISSION_PERCENT", 12.0))


# --- SBP Payment Details ---
SBP_PHONE = os.getenv("SBP_PHONE")
SBP_BANK = os.getenv("SBP_BANK")


# Проверка на наличие токена (критически важная переменная)
if not TOKEN:
    raise ValueError("Необходимо указать TELEGRAM_BOT_TOKEN в файле .env")