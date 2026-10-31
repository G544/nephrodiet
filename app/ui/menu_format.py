WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
SLOTS = [("breakfast", "Завтрак"), ("lunch", "Обед"), ("dinner", "Ужин")]


def day_name(day_index: int) -> str:
    return WEEKDAYS[day_index] if 0 <= day_index < len(WEEKDAYS) else f"День {day_index}"


def ingredient_line(ing: dict) -> str:
    line = f"{ing['name']} — {ing['amount_g']:.0f} {ing['unit']}"
    return f"{line} ({ing['note']})" if ing.get("note") else line


def meal_nutrition_line(meal: dict) -> str:
    return (
        f"на 1 порцию: {meal['calories_kcal']:.0f} ккал · белок {meal['protein_g']:.1f} г · "
        f"соль {meal['salt_g']:.2f} г · жиры {meal['fat_g']:.1f} г · "
        f"углеводы {meal['carbs_g']:.1f} г · калий {meal.get('potassium_mg', 0):.0f} мг · "
        f"фосфор {meal.get('phosphorus_mg', 0):.0f} мг"
    )


def day_title_stats(day) -> str:
    return (
        f"{day.total_calories_kcal:.0f} ккал, "
        f"белок {day.total_protein_g:.1f} г, соль {day.total_salt_g:.2f} г, "
        f"калий {day.total_potassium_mg:.0f} мг, фосфор {day.total_phosphorus_mg:.0f} мг"
    )
