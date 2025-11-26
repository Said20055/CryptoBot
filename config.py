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




# Процент, который получает реферер с каждого обмена своего реферала
REFERRAL_PERCENTAGE = 1.0

# Минимальная сумма в рублях для создания заявки на вывод реферального баланса
MIN_WITHDRAWAL_AMOUNT = 1000 # 1000 RUB


# ==========================================================
# ===== НОВЫЙ МОДУЛЬ: ЛОТЕРЕЯ ==============================
# ==========================================================


# Структура призов в лотерее.
# Формат: (сумма_выигрыша_в_рублях, вес_шанса)
# Чем выше вес, тем чаще выпадает приз. Система автоматически рассчитает проценты.
# Пример: (100, 10) и (1000, 1) означает, что 100 RUB выпадает в 10 раз чаще, чем 1000 RUB.
LOTTERY_PRIZES = [
    (1, 80),       # 10 RUB - самый частый, "утешительный" приз
    (3, 10),       # 50 RUB
    (7, 7),       # 100 RUB
    (10, 2.999),       # 500 RUB
    (100, 0.001),      
]


# Проверка на наличие токена (критически важная переменная)
if not TOKEN:
    raise ValueError("Необходимо указать TELEGRAM_BOT_TOKEN в файле .env")