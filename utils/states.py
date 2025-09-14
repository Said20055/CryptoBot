"""
Состояния FSM для бота.

Этот модуль определяет все состояния конечного автомата (FSM),
используемые для управления диалогами с пользователями.
"""

from aiogram.fsm.state import State, StatesGroup

class TransactionStates(StatesGroup):
    """Состояния для создания транзакции"""
    waiting_for_crypto_amount = State()  # Ожидание ввода суммы в криптовалюте
    waiting_for_rub_amount = State()     # Ожидание ввода суммы в рублях
    waiting_for_payment_method = State() # Ожидание выбора способа оплаты
    waiting_for_phone = State()          # Ожидание номера телефона и банка
    waiting_for_tx_link = State()        # Ожидание ссылки на транзакцию
    waiting_for_operator_reply = State() # Ожидание ответа оператору
