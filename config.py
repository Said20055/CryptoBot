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

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bot:secret@localhost:5432/cryptobot")

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
    "TRX": os.getenv("WALLET_TRX", ""),
    "USDT": os.getenv("WALLET_USDT", ""),
}


# --- Financial Settings ---
# Загружаем числовые значения и преобразуем их в нужный тип (int, float)
# Указываем значения по умолчанию на случай, если они не заданы в .env
NETWORK_FEE_RUB = int(os.getenv("NETWORK_FEE_RUB", 300))
SERVICE_COMMISSION_PERCENT = float(os.getenv("SERVICE_COMMISSION_PERCENT", 15.0))


# --- SBP Payment Details ---
SBP_PHONE = os.getenv("SBP_PHONE")
SBP_BANK = os.getenv("SBP_BANK")




# Процент, который получает реферер с каждого обмена своего реферала
REFERRAL_PERCENTAGE = 10.0

# Через сколько минут заявка закрывается автоматически, если оператор не обработал её.
ORDER_AUTO_CLOSE_MINUTES = int(os.getenv("ORDER_AUTO_CLOSE_MINUTES", 15))

# Интервал уведомлений админов о необработанных заявках (в секундах).
ADMIN_REMINDER_MIN_SECONDS = int(os.getenv("ADMIN_REMINDER_MIN_SECONDS", 120))
ADMIN_REMINDER_MAX_SECONDS = int(os.getenv("ADMIN_REMINDER_MAX_SECONDS", 180))

# Ночное окно по МСК, в которое отправляются напоминания администраторам.
ADMIN_REMINDER_NIGHT_START_HOUR_MSK = int(os.getenv("ADMIN_REMINDER_NIGHT_START_HOUR_MSK", 0))
ADMIN_REMINDER_NIGHT_END_HOUR_MSK = int(os.getenv("ADMIN_REMINDER_NIGHT_END_HOUR_MSK", 8))

# Задержка приветственного сообщения после создания заявки (сек).
ORDER_GREETING_DELAY_SECONDS = int(os.getenv("ORDER_GREETING_DELAY_SECONDS", 5))

# Смещение для отображаемого номера заявки (order_id + ORDER_NUMBER_OFFSET)
ORDER_NUMBER_OFFSET = 9999

# Минимальная сумма в рублях для создания заявки на вывод реферального баланса
MIN_WITHDRAWAL_AMOUNT = 300 # 1000 RUB


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
