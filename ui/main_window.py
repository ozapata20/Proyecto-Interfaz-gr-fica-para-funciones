"""Responsive Tkinter interface for adding and selecting graph functions."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from graphing.intersections import IntersectionPoint, find_intersections
from graphing.plotter import PlotRenderer, PlotSeries
from utils.analysis import FunctionAnalysis, analyze_function
from utils.reader import ExpressionError, ParsedFunction, parse_function


@dataclass
class FunctionItem:
    identifier: str
    expression: str
    function: ParsedFunction
    color: str
    selected: tk.BooleanVar
    row: ttk.Frame


def _next_function_identifier(used: set[str]) -> str:
    index = 5
    while True:
        value = index
        name = ""
        while value >= 0:
            value, remainder = divmod(value, 26)
            name = chr(ord("a") + remainder) + name
            value -= 1
        if name not in used:
            return name
        index += 1


class GraphingApplication:
    """Build and run the complete graphing application window."""

    _PALETTE = ("#137c63", "#d96845", "#3779b7", "#b38222", "#8a5a9e", "#338a91")

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Graficador")
        self.root.geometry("1600x900")
        self.root.minsize(900, 600)
        self.root.configure(background="#f2f4ef")
        self._items: list[FunctionItem] = []
        self._build_styles()
        self._build_layout()
        self._render()

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background="#f2f4ef")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f2f4ef", foreground="#18231d", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground="#18231d")
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 11), foreground="#26332b")
        style.configure("Muted.TLabel", foreground="#728077", font=("Segoe UI", 9))
        style.configure("Count.TLabel", foreground="#137c63", font=("Segoe UI Semibold", 10))
        style.configure("FunctionRow.TFrame", background="#ffffff")
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 9))
        style.configure("Accent.TButton", background="#137c63", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#0e654f"), ("pressed", "#0a5542")])
        style.configure("Info.TButton", font=("Segoe UI Symbol", 12), padding=(6, 4))
        style.configure("TEntry", padding=(10, 9), fieldbackground="#ffffff")
        style.configure("TCheckbutton", background="#ffffff")

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1, uniform="panes")
        self.root.columnconfigure(1, weight=1, uniform="panes")
        self.root.rowconfigure(0, weight=1)

        graph_pane = ttk.Frame(self.root, style="App.TFrame", padding=(24, 22, 18, 22))
        graph_pane.grid(row=0, column=0, sticky="nsew")
        graph_pane.columnconfigure(0, weight=1)
        graph_pane.rowconfigure(1, weight=1)
        graph_pane.rowconfigure(2, weight=0)

        heading = ttk.Frame(graph_pane, style="App.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(heading, text="Function Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="VISUALIZACIÓN CARTESIANA", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))

        chart_frame = ttk.Frame(graph_pane, style="Panel.TFrame", padding=8)
        chart_frame.grid(row=1, column=0, sticky="nsew")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.rowconfigure(1, weight=0)
        self.figure = Figure(figsize=(7.5, 6.5), dpi=100, facecolor="#ffffff")
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.plotter = PlotRenderer(self.figure, self.axes, self.canvas.draw_idle)
        self.canvas.mpl_connect("motion_notify_event", self._on_plot_motion)
        self.toolbar = NavigationToolbar2Tk(self.canvas, chart_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=1, column=0, sticky="ew")
        self.cursor_label = ttk.Label(
            graph_pane,
            text="Cursor: mueve sobre el gráfico para leer coordenadas.",
            style="Muted.TLabel",
        )
        self.cursor_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

        divider = ttk.Separator(self.root, orient="vertical")
        divider.place(relx=0.5, rely=0.04, relheight=0.92, anchor="n")

        control_pane = ttk.Frame(self.root, style="App.TFrame", padding=(28, 28, 24, 22))
        control_pane.grid(row=0, column=1, sticky="nsew")
        control_pane.columnconfigure(0, weight=1)
        control_pane.rowconfigure(7, weight=1)
        control_pane.rowconfigure(9, weight=0)

        ttk.Label(control_pane, text="Funciones", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            control_pane,
            text="Escribe una expresión y activa las curvas que quieras comparar.",
            style="Muted.TLabel",
            wraplength=600,
        ).grid(row=1, column=0, sticky="w", pady=(4, 22))

        ttk.Label(control_pane, text="NUEVA EXPRESIÓN", style="Section.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 8)
        )
        input_row = ttk.Frame(control_pane, style="App.TFrame")
        input_row.grid(row=3, column=0, sticky="ew")
        input_row.columnconfigure(0, weight=1)
        self.expression_var = tk.StringVar()
        self.expression_entry = ttk.Entry(input_row, textvariable=self.expression_var, font=("Consolas", 12))
        self.expression_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.expression_entry.bind("<Return>", self._add_expression)
        ttk.Button(
            input_row,
            text="Añadir +",
            style="Accent.TButton",
            command=self._add_expression,
        ).grid(row=0, column=1)

        self.show_intersections_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            control_pane,
            text="Mostrar intersecciones",
            variable=self.show_intersections_var,
            command=self._toggle_intersections,
        ).grid(row=4, column=0, sticky="w", pady=(12, 0))

        range_row = ttk.Frame(control_pane, style="App.TFrame")
        range_row.grid(row=5, column=0, sticky="ew", pady=(20, 18))
        ttk.Label(range_row, text="Intervalo de x", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.x_min_var = tk.StringVar(value="-10")
        self.x_max_var = tk.StringVar(value="10")
        ttk.Label(range_row, text="de", style="Muted.TLabel").grid(row=0, column=1, padx=(0, 5))
        ttk.Entry(range_row, textvariable=self.x_min_var, width=9).grid(row=0, column=2, padx=(0, 10))
        ttk.Label(range_row, text="a", style="Muted.TLabel").grid(row=0, column=3, padx=(0, 5))
        ttk.Entry(range_row, textvariable=self.x_max_var, width=9).grid(row=0, column=4, padx=(0, 10))
        ttk.Button(range_row, text="Actualizar", command=self._update_range).grid(row=0, column=5)

        list_header = ttk.Frame(control_pane, style="App.TFrame")
        list_header.grid(row=6, column=0, sticky="ew", pady=(0, 9))
        list_header.columnconfigure(0, weight=1)
        ttk.Label(list_header, text="LISTA DE FUNCIONES", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.count_label = ttk.Label(list_header, text="0 activas · 0 total", style="Count.TLabel")
        self.count_label.grid(row=0, column=1, sticky="e")

        list_container = ttk.Frame(control_pane, style="Panel.TFrame", padding=8)
        list_container.grid(row=7, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)
        self.list_canvas = tk.Canvas(list_container, background="#ffffff", highlightthickness=0)
        self.list_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.list_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        self.list_frame = ttk.Frame(self.list_canvas, style="Panel.TFrame")
        self.list_frame.columnconfigure(0, weight=1)
        self.list_window = self.list_canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", self._resize_scroll_region)
        self.list_canvas.bind("<Configure>", self._resize_list_width)
        self.list_canvas.bind_all("<MouseWheel>", self._scroll_list)

        self.intersections_header = ttk.Frame(control_pane, style="App.TFrame")
        self.intersections_header.grid(row=8, column=0, sticky="ew", pady=(14, 8))
        self.intersections_header.columnconfigure(0, weight=1)
        ttk.Label(
            self.intersections_header,
            text="PUNTOS DE INTERSECCIÓN",
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.intersection_count_label = ttk.Label(
            self.intersections_header,
            text="0 puntos",
            style="Count.TLabel",
        )
        self.intersection_count_label.grid(row=0, column=1, sticky="e")

        self.intersections_container = ttk.Frame(control_pane, style="Panel.TFrame", padding=6)
        self.intersections_container.grid(row=9, column=0, sticky="nsew")
        self.intersections_container.columnconfigure(0, weight=1)
        self.intersections_container.rowconfigure(0, weight=1)
        self.intersection_table = ttk.Treeview(
            self.intersections_container,
            columns=("identifier", "coordinates", "functions"),
            show="headings",
            selectmode="browse",
        )
        self.intersection_table.heading("identifier", text="ID")
        self.intersection_table.heading("coordinates", text="Coordenadas (x, y)")
        self.intersection_table.heading("functions", text="Funciones")
        self.intersection_table.column("identifier", width=48, minwidth=42, stretch=False, anchor="center")
        self.intersection_table.column("coordinates", width=150, minwidth=120, stretch=False)
        self.intersection_table.column("functions", width=210, minwidth=120, stretch=True)
        self.intersection_table.grid(row=0, column=0, sticky="nsew")
        intersection_scrollbar = ttk.Scrollbar(
            self.intersections_container,
            orient="vertical",
            command=self.intersection_table.yview,
        )
        intersection_scrollbar.grid(row=0, column=1, sticky="ns")
        self.intersection_table.configure(yscrollcommand=intersection_scrollbar.set)
        self.intersections_header.grid_remove()
        self.intersections_container.grid_remove()
        self._intersection_points: list[IntersectionPoint] = []

        self.empty_list_label = ttk.Label(
            self.list_frame,
            text="Aún no hay funciones. Prueba x^2, 2^x o ln(x).",
            style="Muted.TLabel",
            padding=(12, 16),
        )
        self.empty_list_label.grid(row=0, column=0, sticky="w")

        self.expression_entry.focus_set()

    def _add_expression(self, _event: tk.Event[tk.Misc] | None = None) -> str:
        expression = self.expression_var.get().strip()
        try:
            function = parse_function(expression)
        except ExpressionError as error:
            messagebox.showerror("Expresión no válida", str(error), parent=self.root)
            self.expression_entry.focus_set()
            return "break"

        color = self._PALETTE[len(self._items) % len(self._PALETTE)]
        selected = tk.BooleanVar(value=True)
        row = ttk.Frame(self.list_frame, style="FunctionRow.TFrame", padding=(8, 7))
        identifier = self._next_function_identifier()
        item = FunctionItem(identifier, expression, function, color, selected, row)
        self._items.append(item)
        self._refresh_list()
        self.expression_var.set("")
        self.expression_entry.focus_set()
        self._render()
        return "break"

    def _refresh_list(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self._items:
            ttk.Label(
                self.list_frame,
                text="Aún no hay funciones. Prueba x^2, 2^x o ln(x).",
                style="Muted.TLabel",
                padding=(12, 16),
            ).grid(row=0, column=0, sticky="w")
        for index, item in enumerate(self._items):
            item.row = ttk.Frame(self.list_frame, style="FunctionRow.TFrame", padding=(8, 7))
            item.row.grid(row=index, column=0, sticky="ew", pady=2)
            item.row.columnconfigure(2, weight=1)
            ttk.Checkbutton(
                item.row,
                variable=item.selected,
                command=self._render,
            ).grid(row=0, column=0, padx=(0, 5))
            tk.Frame(item.row, width=10, height=10, background=item.color).grid(
                row=0, column=1, padx=(0, 10)
            )
            ttk.Label(
                item.row,
                text=f"{item.identifier}(x) = {item.expression}",
                style="Section.TLabel",
                font=("Consolas", 11),
            ).grid(row=0, column=2, sticky="w")
            ttk.Button(
                item.row,
                text="ⓘ",
                style="Info.TButton",
                width=3,
                command=lambda current=item: self._show_function_info(current),
            ).grid(row=0, column=3, padx=(8, 0))
            ttk.Button(
                item.row,
                text="Quitar",
                width=8,
                command=lambda current=item: self._remove_item(current),
            ).grid(row=0, column=4, padx=(8, 0))
        active_count = sum(item.selected.get() for item in self._items)
        self.count_label.configure(text=f"{active_count} activas · {len(self._items)} total")
        self.list_frame.update_idletasks()
        self._resize_scroll_region()

    def _next_function_identifier(self) -> str:
        return _next_function_identifier({item.identifier for item in self._items})

    def _show_function_info(self, item: FunctionItem) -> None:
        try:
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min >= x_max:
                x_min = x_max = None
        except ValueError:
            x_min = x_max = None

        try:
            analysis = analyze_function(item.function, x_min, x_max)
        except (ArithmeticError, TypeError, ValueError, np.linalg.LinAlgError) as error:
            messagebox.showerror(
                "No se pudo analizar la función",
                str(error),
                parent=self.root,
            )
            return

        window = tk.Toplevel(self.root)
        window.title(f"Información de {item.identifier}(x)")
        window.transient(self.root)
        window.resizable(False, False)
        window.configure(background="#f2f4ef")
        content = ttk.Frame(window, style="App.TFrame", padding=22)
        content.grid(sticky="nsew")
        ttk.Label(
            content,
            text=f"{item.identifier}(x) = {item.expression}",
            style="Title.TLabel",
            wraplength=500,
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))

        if analysis.is_polynomial:
            function_type = (
                "Polinomio nulo"
                if analysis.is_zero_function
                else f"Polinomio de grado {analysis.degree}"
            )
        else:
            function_type = "Función no polinómica"
        x_intercepts = self._format_x_intercepts(analysis, x_min, x_max)
        y_intercept = self._format_intercept(analysis.y_intercept)
        if analysis.degree == 1:
            rows = [
                ("Tipo", function_type),
                ("Pendiente", self._format_value(analysis.slope)),
                ("Intersección con el eje X", x_intercepts),
                ("Intersección con el eje Y", y_intercept),
            ]
        elif analysis.degree == 2:
            rows = [
                ("Tipo", function_type),
                ("Concavidad", analysis.concavity or "No definida"),
                ("Vértice", self._format_vertex(analysis)),
                ("Intersecciones con el eje X", x_intercepts),
                ("Intersección con el eje Y", y_intercept),
                ("Eje de simetría", self._format_axis(analysis.symmetry_axis)),
            ]
        elif analysis.degree == 3:
            rows = [
                ("Tipo", function_type),
                ("Intersecciones con el eje X", x_intercepts),
                ("Intersección con el eje Y", y_intercept),
                ("Punto de inflexión", self._format_point(analysis.inflection_point)),
            ]
        else:
            rows = [
                ("Tipo", function_type),
                ("Intersecciones con el eje X", x_intercepts),
                ("Intersección con el eje Y", y_intercept),
                ("Vértice", self._format_vertex(analysis)),
            ]
        for row_index, (title, value) in enumerate(rows):
            title_row = row_index * 2 + 1
            ttk.Label(content, text=title, style="Section.TLabel").grid(
                row=title_row, column=0, sticky="w", pady=(8, 2)
            )
            ttk.Label(
                content,
                text=value,
                style="Muted.TLabel",
                wraplength=500,
                justify="left",
            ).grid(row=title_row + 1, column=0, sticky="w")

        ttk.Button(content, text="Cerrar", command=window.destroy).grid(
            row=len(rows) * 2 + 1, column=0, sticky="e", pady=(18, 0)
        )
        window.update_idletasks()
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        x = max(0, min(x, self.root.winfo_screenwidth() - width))
        y = max(0, min(y, self.root.winfo_screenheight() - height))
        window.geometry(f"+{x}+{y}")
        window.grab_set()

    @staticmethod
    def _format_value(value: float | None) -> str:
        return "No definida" if value is None else f"{value:.6g}"

    @staticmethod
    def _format_axis(value: float | None) -> str:
        return "No definido" if value is None else f"x = {value:.6g}"

    @staticmethod
    def _format_point(point: tuple[float, float] | None) -> str:
        if point is None:
            return "No definido"
        return f"({point[0]:.6g}, {point[1]:.6g})"

    @staticmethod
    def _format_intercept(value: float | None) -> str:
        return "No definida para x = 0" if value is None else f"(0, {value:.6g})"

    @staticmethod
    def _format_x_intercepts(
        analysis: FunctionAnalysis,
        x_min: float | None,
        x_max: float | None,
    ) -> str:
        if analysis.is_zero_function:
            return "Todos los puntos del eje X"
        if analysis.x_intercepts is None:
            return "No se pudieron calcular"
        if not analysis.x_intercepts:
            return "No hay intersecciones reales"
        coordinates = ", ".join(f"({value:.6g}, 0)" for value in analysis.x_intercepts)
        if analysis.is_polynomial:
            return coordinates
        if x_min is None or x_max is None:
            return "No se pudieron calcular (intervalo de x no válido)"
        return f"{coordinates} (aproximadas en [{x_min:g}, {x_max:g}])"

    @staticmethod
    def _format_vertex(analysis: FunctionAnalysis) -> str:
        if analysis.vertex is not None:
            x_value, y_value = analysis.vertex
            return f"({x_value:.6g}, {y_value:.6g})"
        if analysis.is_polynomial and analysis.degree == 2:
            return "No definido"
        return "Solo se calcula para polinomios cuadráticos"

    def _remove_item(self, item: FunctionItem) -> None:
        self._items.remove(item)
        self._refresh_list()
        self._render()

    def _resize_scroll_region(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    def _resize_list_width(self, event: tk.Event[tk.Misc]) -> None:
        self.list_canvas.itemconfigure(self.list_window, width=event.width)

    def _scroll_list(self, event: tk.Event[tk.Misc]) -> None:
        if self.list_canvas.winfo_exists():
            self.list_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_plot_motion(self, event: object) -> None:
        coordinates = self.plotter.on_mouse_move(event)
        if coordinates is None:
            self.cursor_label.configure(text="Cursor: mueve sobre el gráfico para leer coordenadas.")
            return
        self.cursor_label.configure(text=f"Cursor: x = {coordinates[0]:.5g}    y = {coordinates[1]:.5g}")

    def _toggle_intersections(self) -> None:
        if self.show_intersections_var.get():
            self.intersections_header.grid()
            self.intersections_container.grid()
            self.intersections_container.master.rowconfigure(7, weight=2)
            self.intersections_container.master.rowconfigure(9, weight=1)
        else:
            self.intersections_header.grid_remove()
            self.intersections_container.grid_remove()
            self.intersections_container.master.rowconfigure(7, weight=1)
            self.intersections_container.master.rowconfigure(9, weight=0)
        self._render()

    def _refresh_intersections(self, points: list[IntersectionPoint]) -> None:
        self.intersection_count_label.configure(text=f"{len(points)} puntos")
        self.intersection_table.delete(*self.intersection_table.get_children())
        if not points:
            self.intersection_table.insert("", "end", values=("", "Sin intersecciones", ""))
            return
        for point in points:
            self.intersection_table.insert(
                "",
                "end",
                values=(
                    point.identifier,
                    f"({point.x:.6g}, {point.y:.6g})",
                    " · ".join(point.expressions),
                ),
            )

    def _update_range(self) -> None:
        try:
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min >= x_max:
                raise ValueError
        except ValueError:
            messagebox.showerror("Intervalo no válido", "El límite inicial debe ser menor que el final.", parent=self.root)
            return
        self._render()

    def _render(self) -> None:
        try:
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min >= x_max:
                return
        except ValueError:
            return
        selected = [
            PlotSeries(f"{item.identifier}(x) = {item.expression}", item.function, item.color)
            for item in self._items
            if item.selected.get()
        ]
        self.count_label.configure(text=f"{len(selected)} activas · {len(self._items)} total")
        self._intersection_points = (
            find_intersections(selected, x_min, x_max)
            if self.show_intersections_var.get()
            else []
        )
        self._refresh_intersections(self._intersection_points)
        self.plotter.render(selected, x_min, x_max, self._intersection_points)

    def run(self) -> None:
        self.root.mainloop()