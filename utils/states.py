"""
Состояния FSM для бота.

Этот модуль определяет все состояния конечного автомата (FSM),
используемые для управления диалогами с пользователями.
"""

from aiogram.fsm.state import State, StatesGroup

class UserPromoStates(StatesGroup):
    waiting_for_code = State()

class PromoStates(StatesGroup):
    waiting_for_promo_code = State()

class TransactionStates(StatesGroup):
    """Состояния для создания транзакции"""
    waiting_for_crypto_amount = State()  # Ожидание ввода суммы в криптовалюте
    waiting_for_rub_amount = State()     # Ожидание ввода суммы в рублях
    waiting_for_user_requisites = State()
    waiting_for_operator_reply = State() # Ожидание ответа оператору

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State() 