"""Focused tests for mathematical expression parsing and evaluation."""

import unittest

import numpy as np

from utils.reader import ExpressionError, parse_function


class ParseFunctionTests(unittest.TestCase):
    def test_polynomial_with_implicit_multiplication(self) -> None:
        function = parse_function("x^3 - 2x + 1")
        np.testing.assert_allclose(function(np.array([-2.0, 0.0, 2.0])), [-3.0, 1.0, 5.0])

    def test_exponential_forms(self) -> None:
        values = np.array([0.0, 1.0])
        np.testing.assert_allclose(parse_function("e^x")(values), [1.0, np.e])
        np.testing.assert_allclose(parse_function("2^x")(values), [1.0, 2.0])

    def test_logarithms_and_explicit_base(self) -> None:
        self.assertAlmostEqual(float(parse_function("ln(e)")(1.0)), 1.0)
        self.assertAlmostEqual(float(parse_function("log(100)")(1.0)), 2.0)
        self.assertAlmostEqual(float(parse_function("log(8, 2)")(1.0)), 3.0)

    def test_common_functions_and_implicit_parentheses(self) -> None:
        values = np.array([1.0, 2.0])
        np.testing.assert_allclose(parse_function("2(x + 1)")(values), [4.0, 6.0])
        np.testing.assert_allclose(parse_function("sin(x)")(values), np.sin(values))

    def test_rejects_unknown_names_and_python_code(self) -> None:
        for expression in ("unknown(x)", "__import__('os')", "x // 2", "sin()"):
            with self.subTest(expression=expression), self.assertRaises(ExpressionError):
                parse_function(expression)


if __name__ == "__main__":
    unittest.main()