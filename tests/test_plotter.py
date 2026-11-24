"""Tests for graph rendering and viewport behavior."""

import unittest

import numpy as np
from matplotlib.figure import Figure

from graphing.plotter import PlotRenderer, PlotSeries


class PlotRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        figure = Figure()
        axes = figure.add_subplot(111)
        self.renderer = PlotRenderer(figure, axes, lambda: None)
        self.axes = axes
        self.series = [PlotSeries("f(x) = x", lambda x: np.asarray(x), "#137c63")]

    def test_preserves_zoom_when_redrawing(self) -> None:
        self.renderer.render(self.series, -10, 10)
        self.axes.set_xlim(-2.5, 3.25)
        self.axes.set_ylim(-4, 5)
        expected_xlim = self.axes.get_xlim()
        expected_ylim = self.axes.get_ylim()

        self.renderer.render(self.series, -10, 10, dark_mode=True, preserve_view=True)

        self.assertEqual(self.axes.get_xlim(), expected_xlim)
        self.assertEqual(self.axes.get_ylim(), expected_ylim)

    def test_can_reset_view_for_new_configured_interval(self) -> None:
        self.renderer.render(self.series, -10, 10)
        self.axes.set_xlim(-2.5, 3.25)

        self.renderer.render(self.series, -5, 5, preserve_view=False)

        self.assertEqual(self.axes.get_xlim(), (-5, 5))

    def test_resets_equal_aspect_from_geometry_before_rendering_functions(self) -> None:
        self.axes.set_aspect("equal", adjustable="box")

        self.renderer.render(self.series, -10, 10)

        self.assertEqual(self.axes.get_aspect(), "auto")


if __name__ == "__main__":
    unittest.main()
