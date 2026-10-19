"""Tests for drawing geometric figures in two and three dimensions."""

import unittest

from matplotlib.figure import Figure

from graphing.geometries import GeometricFigure, render_geometry_2d, render_geometry_3d


class GeometryRenderingTests(unittest.TestCase):
    def test_renders_point_circle_and_rectangle_in_2d(self) -> None:
        figure = Figure()
        axes = figure.add_subplot(111)
        figures = [
            GeometricFigure("Punto 1", "Punto", {"x": 1, "y": 2}, "#137c63"),
            GeometricFigure("Círculo 2", "Círculo", {"x": 0, "y": 0, "r": 2}, "#d96845"),
            GeometricFigure(
                "Rectángulo 3",
                "Rectángulo",
                {"x": -1, "y": -1, "width": 2, "height": 1},
                "#3779b7",
            ),
        ]

        render_geometry_2d(axes, figures, (-5, 5), None)

        self.assertEqual(len(axes.patches), 2)
        self.assertEqual(len(axes.collections), 1)
        self.assertEqual(axes.get_xlim(), (-5, 5))
        self.assertEqual(axes.get_ylim(), (-5, 5))

    def test_renders_sphere_and_plane_in_3d(self) -> None:
        figure = Figure()
        axes = figure.add_subplot(111, projection="3d")
        figures = [
            GeometricFigure("Esfera 1", "Esfera", {"x": 0, "y": 0, "z": 0, "r": 2}, "#137c63"),
            GeometricFigure("Plano 2", "Plano", {"a": 1, "b": -1, "c": 0}, "#d96845"),
        ]

        render_geometry_3d(axes, figures, (-5, 5), (-4, 4))

        self.assertEqual(len(axes.collections), 2)
        self.assertEqual(axes.get_xlim(), (-5, 5))
        self.assertEqual(axes.get_ylim(), (-5, 5))
        self.assertEqual(axes.get_zlim(), (-4, 4))

    def test_preserves_view_when_toggling_figure_visibility(self) -> None:
        figure = Figure()
        axes = figure.add_subplot(111)
        axes.set_xlim(-2, 3)
        axes.set_ylim(-4, 5)

        render_geometry_2d(
            axes,
            [GeometricFigure("Círculo 1", "Círculo", {"x": 0, "y": 0, "r": 1}, "#137c63")],
            (-10, 10),
            None,
            preserve_view=True,
        )

        self.assertEqual(axes.get_xlim(), (-2, 3))
        self.assertEqual(axes.get_ylim(), (-4, 5))


if __name__ == "__main__":
    unittest.main()
