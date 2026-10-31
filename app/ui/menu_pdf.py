from pathlib import Path

from fpdf import FPDF

from app.ui.menu_format import (
    SLOTS,
    day_name,
    day_title_stats,
    ingredient_line,
    meal_nutrition_line,
)

_FONTS = Path(__file__).parent / "fonts"
_FONT = "DejaVu"


def build_menu_pdf(menu, days, warnings) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font(_FONT, "", str(_FONTS / "DejaVuSans.ttf"))
    pdf.add_font(_FONT, "B", str(_FONTS / "DejaVuSans-Bold.ttf"))
    pdf.add_page()

    def write(text: str, size: float, bold: bool = False, gap: float = 1.5) -> None:
        pdf.set_font(_FONT, "B" if bold else "", size)
        pdf.multi_cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(gap)

    write(f"Меню на неделю с {menu.week_start_date}", 18, bold=True, gap=2)
    write(
        f"Целевая калорийность: {menu.calorie_target_kcal:.0f} ккал/день "
        f"(минимум {menu.calorie_target_min:.0f}, максимум {menu.calorie_target_max:.0f})",
        10,
    )

    write("Проверка недели", 13, bold=True)
    if menu.review_status == "warning":
        write(f"⚠ Проверка недели выявила проблемы: {menu.review_summary_ru}", 10)
        for w in warnings:
            prefix = f"{day_name(w.day_index)}: " if w.day_index is not None else ""
            write(f"•  {prefix}{w.message_ru}", 10, gap=0.5)
    else:
        write(menu.review_summary_ru or "Неделя в пределах ограничений.", 10)

    for i, day in enumerate(days):
        if i:
            pdf.add_page()
        else:
            pdf.ln(4)
        write(f"{day_name(day.day_index)} ({day.date})", 15, bold=True)
        write(f"Итого за день: {day_title_stats(day)}", 9)
        if day.adjustment_notes:
            write(day.adjustment_notes, 9)
        for slot, slot_label in SLOTS:
            meal = day.meals[slot]
            pdf.ln(2)
            write(f"{slot_label}: {meal['name']}", 12, bold=True, gap=1)
            write(meal_nutrition_line(meal), 8.5)
            write(f"Ингредиенты (на {meal.get('servings', 2)} порции):", 10, bold=True, gap=0.5)
            for ing in meal["ingredients"]:
                write(f"•  {ingredient_line(ing)}", 10, gap=0.3)
            pdf.ln(1)
            write("Приготовление:", 10, bold=True, gap=0.5)
            write(meal["instructions"], 10)

    return bytes(pdf.output())
