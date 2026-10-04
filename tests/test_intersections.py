"""Tests for numerical function-intersection detection."""

import unittest

from graphing.intersections import find_intersections
from graphing.plotter import PlotSeries
from utils.reader import parse_function


def series(expression: str) -> PlotSeries:
    return PlotSeries(expression, parse_function(expression), "#137c63")


class FindIntersectionsTests(unittest.TestCase):
    def test_finds_and_orders_multiple_crossings(self) -> None:
        points = find_intersections([series("x^2"), series("1")], -2, 2)
        self.assertEqual([point.identifier for point in points], ["A", "B"])
        self.assertAlmostEqual(points[0].x, -1.0, places=7)
        self.assertAlmostEqual(points[1].x, 1.0, places=7)
        self.assertAlmostEqual(points[0].y, 1.0, places=7)

    def test_finds_tangent_between_sample_positions(self) -> None:
        points = find_intersections([series("(x - 0.123)^2"), series("0")], -1, 1)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].identifier, "A")
        self.assertAlmostEqual(points[0].x, 0.123, places=6)
        self.assertAlmostEqual(points[0].y, 0.0, places=8)

    def test_merges_a_shared_intersection_of_three_functions(self) -> None:
        points = find_intersections([series("x"), series("-x"), series("0")], -2, 2)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].identifier, "A")
        self.assertEqual(len(points[0].expressions), 3)

    def test_does_not_report_a_vertical_asymptote_as_an_intersection(self) -> None:
        points = find_intersections([series("1 / (x - 0.123)"), series("0")], -1, 1)
        self.assertEqual(points, [])


if __name__ == "__main__":
    unittest.main()