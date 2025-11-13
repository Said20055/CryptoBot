# utils/helpers.py

"""
Вспомогательные функции (хелперы) для различных модулей бота.
"""
import random
from typing import List, Tuple
from datetime import timedelta

def calculate_lottery_win(prizes: List[Tuple[int, int]]) -> int:
    """
    Рассчитывает выигрыш в лотерее на основе списка призов и их весов.

    Args:
        prizes: Список кортежей вида (сумма_выигрыша, вес_шанса).
                Пример: [(10, 70), (100, 20), (1000, 1)]

    Returns:
        Случайно выбранная сумма выигрыша.
    """
    # Разделяем призы и их веса на два отдельных списка
    amounts = [prize[0] for prize in prizes]
    weights = [prize[1] for prize in prizes]
    
    # Функция random.choices идеально подходит для взвешенного случайного выбора.
    # Она возвращает список из k элементов, поэтому мы берем первый [0].
    winner_amount = random.choices(amounts, weights=weights, k=1)[0]
    
    return winner_amount


def format_timedelta(duration: timedelta) -> str:
    """
    Красиво форматирует объект timedelta в строку "ЧЧ:ММ:СС".
    """
    if not isinstance(duration, timedelta) or duration.total_seconds() <= 0:
        return "00:00:00"
        
    # total_seconds() возвращает общее количество секунд
    total_seconds = int(duration.total_seconds())
    
    # Вычисляем часы, минуты и секунды
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Форматируем в строку с ведущими нулями (01:05:09)
    return f"{hours:02}:{minutes:02}:{seconds:02}"