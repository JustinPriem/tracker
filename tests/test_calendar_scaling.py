"""Reine Funktions-Tests fuer die absolute Kalender-Skalierung (Desktop).
Kein pytest-Framework noetig - direkt ausfuehren mit:
    python tests/test_calendar_scaling.py
Importiert repxo.py direkt; das ist side-effect-frei dank des
`if __name__ == "__main__":`-Guards am Dateiende.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import repxo


def test_value_to_radius_zero_reps_for_full_size():
    assert repxo.value_to_radius(repxo.REPS_FOR_FULL_SIZE) == repxo.MAX_CIRCLE_RADIUS


def test_value_to_radius_half_reps_is_half_radius():
    half = repxo.REPS_FOR_FULL_SIZE // 2
    assert repxo.value_to_radius(half) == round(repxo.MAX_CIRCLE_RADIUS * 0.5)


def test_value_to_radius_caps_above_full_size():
    assert repxo.value_to_radius(repxo.REPS_FOR_FULL_SIZE * 3) == repxo.MAX_CIRCLE_RADIUS


def test_value_to_radius_small_value_has_technical_floor_not_zero():
    assert repxo.value_to_radius(1) >= repxo.MIN_RENDER_RADIUS
    assert repxo.value_to_radius(1) > 0


def test_value_to_color_zero_reps_for_full_size_is_low_color():
    assert repxo.value_to_color(0) == "#3a1f14"


def test_value_to_color_full_size_is_high_color():
    assert repxo.value_to_color(repxo.REPS_FOR_FULL_SIZE) == "#ff5722"


def test_value_to_color_caps_above_full_size():
    assert repxo.value_to_color(repxo.REPS_FOR_FULL_SIZE * 3) == "#ff5722"


TESTS = [
    test_value_to_radius_zero_reps_for_full_size,
    test_value_to_radius_half_reps_is_half_radius,
    test_value_to_radius_caps_above_full_size,
    test_value_to_radius_small_value_has_technical_floor_not_zero,
    test_value_to_color_zero_reps_for_full_size_is_low_color,
    test_value_to_color_full_size_is_high_color,
    test_value_to_color_caps_above_full_size,
]

if __name__ == "__main__":
    failures = 0
    for test in TESTS:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        except AttributeError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        except TypeError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    if failures:
        print(f"\n{failures} Test(s) fehlgeschlagen")
        sys.exit(1)
    print(f"\nAlle {len(TESTS)} Tests bestanden")
