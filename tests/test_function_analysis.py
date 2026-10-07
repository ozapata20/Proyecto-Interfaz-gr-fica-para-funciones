"""Tests for function characteristics and labels."""

import unittest

from ui.main_window import _next_function_identifier
from utils.analysis import analyze_function
from utils.reader import parse_function


class FunctionAnalysisTests(unittest.TestCase):
    def test_linear_slope_and_intercepts(self) -> None:
        result = analyze_function(parse_function("2x - 6"))
        self.assertEqual(result.degree, 1)
        self.assertEqual(result.slope, 2.0)
        self.assertEqual(result.x_intercepts, (3.0,))
        self.assertEqual(result.y_intercept, -6.0)

    def test_quadratic_intercepts_and_vertex(self) -> None:
        result = analyze_function(parse_function("x^2 - 4x + 3"))
        self.assertTrue(result.is_polynomial)
        self.assertEqual(result.degree, 2)
        self.assertEqual(result.x_intercepts, (1.0, 3.0))
        self.assertEqual(result.y_intercept, 3.0)
        self.assertEqual(result.vertex, (2.0, -1.0))
        self.assertEqual(result.concavity, "hacia arriba")
        self.assertEqual(result.symmetry_axis, 2.0)

    def test_quadratic_concavity_points_down_for_negative_leading_coefficient(self) -> None:
        result = analyze_function(parse_function("-2x^2 + 4x + 1"))
        self.assertEqual(result.concavity, "hacia abajo")
        self.assertEqual(result.vertex, (1.0, 3.0))
        self.assertEqual(result.symmetry_axis, 1.0)

    def test_cubic_intercepts_and_inflection_point(self) -> None:
        result = analyze_function(parse_function("x^3 - 3x^2 + 2"))
        self.assertEqual(result.degree, 3)
        self.assertIsNotNone(result.x_intercepts)
        assert result.x_intercepts is not None
        self.assertEqual(len(result.x_intercepts), 3)
        for actual, expected in zip(
            result.x_intercepts,
            (-0.7320508075688772, 1.0, 2.732050807568877),
        ):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(result.y_intercept, 2.0)
        self.assertEqual(result.inflection_point, (1.0, 0.0))

    def test_non_polynomial_roots_are_approximated_in_the_interval(self) -> None:
        result = analyze_function(parse_function("sin(x)"), -4, 4)
        self.assertFalse(result.is_polynomial)
        self.assertIsNotNone(result.x_intercepts)
        assert result.x_intercepts is not None
        self.assertEqual(len(result.x_intercepts), 3)
        self.assertAlmostEqual(result.x_intercepts[0], -3.14159265, places=6)
        self.assertAlmostEqual(result.x_intercepts[1], 0.0, places=6)
        self.assertAlmostEqual(result.x_intercepts[2], 3.14159265, places=6)

    def test_y_intercept_is_reported_as_undefined_when_needed(self) -> None:
        result = analyze_function(parse_function("ln(x)"), -2, 2)
        self.assertIsNone(result.y_intercept)

    def test_asymptote_is_not_reported_as_an_x_intercept(self) -> None:
        result = analyze_function(parse_function("1 / (x - 0.123)"), -1, 1)
        self.assertEqual(result.x_intercepts, ())


class FunctionIdentifierTests(unittest.TestCase):
    def test_uses_first_available_function_name(self) -> None:
        self.assertEqual(_next_function_identifier(set()), "f")
        self.assertEqual(_next_function_identifier({"f"}), "g")
        self.assertEqual(_next_function_identifier({"f", "g", "h"}), "i")

    def test_continues_with_unique_names_after_z(self) -> None:
        used = set("fghijklmnopqrstuvwxyz")
        self.assertEqual(_next_function_identifier(used), "aa")


if __name__ == "__main__":
    unittest.main()
