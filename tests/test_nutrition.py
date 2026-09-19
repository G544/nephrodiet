import pytest

from app.domain.nutrition import bmr_mifflin_st_jeor, calculate_calorie_target, tdee


def test_bmr_male_reference_value():
    # 30yo male, 80kg, 180cm: 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
    assert bmr_mifflin_st_jeor(80, 180, 30, "male") == pytest.approx(1780)


def test_bmr_female_reference_value():
    # 30yo female, 65kg, 165cm: 10*65 + 6.25*165 - 5*30 - 161 = 650 + 1031.25 - 150 - 161 = 1370.25
    assert bmr_mifflin_st_jeor(65, 165, 30, "female") == pytest.approx(1370.25)


def test_tdee_applies_activity_multiplier():
    bmr = bmr_mifflin_st_jeor(80, 180, 30, "male")
    assert tdee(80, 180, 30, "male", "sedentary") == pytest.approx(bmr * 1.2)
    assert tdee(80, 180, 30, "male", "active") == pytest.approx(bmr * 1.725)


def test_maintenance_target_equals_tdee_and_floor_never_below():
    target = calculate_calorie_target(80, 180, 30, "male", "moderate", "maintenance")
    expected_tdee = tdee(80, 180, 30, "male", "moderate")
    assert target.target_kcal == pytest.approx(expected_tdee)
    assert target.min_kcal == pytest.approx(target.target_kcal)
    assert target.max_kcal > target.target_kcal


def test_weight_gain_target_is_a_surplus_over_maintenance():
    maintenance = calculate_calorie_target(80, 180, 30, "male", "moderate", "maintenance")
    gain = calculate_calorie_target(80, 180, 30, "male", "moderate", "weight_gain")
    assert gain.target_kcal > maintenance.target_kcal
    assert gain.min_kcal == pytest.approx(gain.target_kcal)


def test_max_kcal_gives_headroom_above_target():
    target = calculate_calorie_target(70, 170, 40, "female", "light", "weight_gain")
    assert target.max_kcal == pytest.approx(target.target_kcal * 1.2)
