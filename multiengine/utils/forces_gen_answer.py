"""
Модуль для генерации допустимых значений углов с учетом толерансов.

Этот модуль обрабатывает исходное состояние студента и генерирует 
допустимые диапазоны значений с учетом угловых толерансов.
"""

import json
from typing import Dict, List, Any


def _should_revert_arrow(variant: str) -> bool:
    """
    Определяет, нужно ли инвертировать направление стрелки.
    
    Args:
        variant (str): Вариант значения
        
    Returns:
        bool: True, если вариант начинается с 'x', иначе False
    """
    return variant.startswith('x')


def _normalize_angle(angle: int) -> int:
    """
    Нормализует угол в диапазон [0, 360).
    
    Args:
        angle (int): Исходный угол
        
    Returns:
        int: Нормализованный угол
    """
    return angle % 360


def generate_tolerances(student_state: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Генерирует допустимые значения с учетом толерансов для каждого элемента.
    
    Args:
        student_state (Dict[str, List[str]]): Исходное состояние с ключами и вариантами
        
    Returns:
        Dict[str, Any]: Словарь с допустимыми значениями для каждого ключа
    """
    tolerances = {}
    result = {}
    
    # Базовые толерансы [-1, 0, 1]
    BASE_TOLERANCE = [-1, 0, 1]
    
    for key, variants in student_state.items():
        tolerances[key] = {}
        or_dict = {"or-and": []}
        
        for variant in variants:
            # Создаем список толерансов
            tolerance_values = [BASE_TOLERANCE.copy()]
            
            # Если нужно инвертировать стрелку, добавляем дополнительные толерансы
            clean_variant = variant
            if _should_revert_arrow(variant):
                inverted_tolerance = [180 + delta for delta in BASE_TOLERANCE]
                tolerance_values.append(inverted_tolerance)
                clean_variant = variant.replace('x', '', 1)
            
            tolerances[key][clean_variant] = tolerance_values
            
            # Разбираем вариант на компоненты
            variant_parts = clean_variant.split('_')
            base_name = variant_parts[0]
            base_angle = int(variant_parts[1])
            
            # Генерируем все возможные варианты с учетом толерансов
            variant_list = []
            for tolerance_group in tolerance_values:
                for delta in tolerance_group:
                    new_angle = base_angle + delta
                    normalized_angle = _normalize_angle(new_angle)
                    variant_list.append(f"{base_name}_{normalized_angle}")
            
            or_dict["or-and"].append(variant_list)
        
        result[key] = or_dict
    
    return result


def main() -> None:
    """
    Основная функция для генерации и вывода результата.
    """
    # Исходные данные
    student_state = {
        "iF": ["xiF_90", "xiF_0"], 
        "iE": ["iE_90"]
    }
    
    # Генерация толерансов
    processed_state = generate_tolerances(student_state)
    
    # Формирование и вывод результата
    answer = {"answer": processed_state}
    answer_json = json.dumps(answer, ensure_ascii=False)
    print(answer_json)


if __name__ == "__main__":
    main()