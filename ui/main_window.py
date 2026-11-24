"""Responsive Tkinter interface for adding and selecting graph functions."""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

import numpy as np
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk

from graphing.geometries import GeometricFigure, render_geometry_2d, render_geometry_3d
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


@dataclass
class GeometryItem:
    figure: GeometricFigure
    selected: tk.BooleanVar
    row: ttk.Frame


class GraphNavigationToolbar(NavigationToolbar2Tk):
    """Use Home to fit the current set of visible functions."""

    def __init__(
        self,
        canvas: FigureCanvasTkAgg,
        window: ttk.Frame,
        reset_view: Callable[[], None],
    ) -> None:
        self._reset_view = reset_view
        super().__init__(canvas, window, pack_toolbar=False)

    def home(self) -> None:
        self._nav_stack.clear()
        self._reset_view()
        self.push_current()


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

    _PALETTE = ("#28c5f5", "#0077b6", "#56d8ff", "#00a8cc", "#5eb8ff", "#74d5d6")

    def __init__(self) -> None:
        assets_directory = Path(__file__).resolve().parent.parent / "assets"
        if sys.platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GraphiX.Studio")
        self.root = tk.Tk()
        self.root.title("GraphiX")
        self.root.geometry("1600x900")
        self.root.minsize(900, 600)
        self.root.configure(background="#eef7fb")
        self._app_icon = tk.PhotoImage(file=str(assets_directory / "GraphiX.png"))
        self.root.iconphoto(True, self._app_icon)
        self.root.iconbitmap(str(assets_directory / "GraphiX.ico"))
        try:
            self._studio_logo = tk.PhotoImage(file=str(assets_directory / "Logo2.png")).subsample(4, 4)
        except tk.TclError:
            self._studio_logo = None
        try:
            gear_image = Image.open(assets_directory / "Engranaje.png").convert("RGBA")
            gear_image = gear_image.resize((34, 34), Image.Resampling.LANCZOS)
            self._gear_icon = ImageTk.PhotoImage(gear_image)
            menu_image = Image.open(assets_directory / "Menu.png").convert("RGBA")
            menu_image = menu_image.resize((34, 34), Image.Resampling.LANCZOS)
            self._menu_icon = ImageTk.PhotoImage(menu_image)
            panel_image = Image.open(assets_directory / "icon3.png").convert("RGBA")
            panel_image = panel_image.resize((38, 36), Image.Resampling.LANCZOS)
            self._panel_icon_right = ImageTk.PhotoImage(panel_image)
            self._panel_icon_left = ImageTk.PhotoImage(panel_image.transpose(Image.Transpose.ROTATE_180))
        except (OSError, tk.TclError):
            self._gear_icon = None
            self._menu_icon = None
            self._panel_icon_right = None
            self._panel_icon_left = None
        self._items: list[FunctionItem] = []
        self._geometry_items: dict[str, list[GeometryItem]] = {
            "Geometría 2D": [],
            "Geometría 3D": [],
        }
        self._geometry_panes: dict[str, ttk.Frame] = {}
        self._geometry_selectors: dict[str, ttk.Combobox] = {}
        self._geometry_field_frames: dict[str, ttk.Frame] = {}
        self._geometry_fields: dict[str, dict[str, ttk.Entry]] = {}
        self._geometry_list_frames: dict[str, ttk.Frame] = {}
        self._geometry_list_canvases: dict[str, tk.Canvas] = {}
        self._geometry_counts: dict[str, ttk.Label] = {}
        self._geometry_counter = 0
        self._mode = "Funciones"
        self._projection = "2d"
        self._controls_visible = True
        self._dark_mode_var = tk.BooleanVar(value=False)
        self.show_intersections_var = tk.BooleanVar(value=False)
        self.x_min_var = tk.StringVar(value="-10")
        self.x_max_var = tk.StringVar(value="10")
        self.y_min_var = tk.StringVar()
        self.y_max_var = tk.StringVar()
        self._pending_dark_mode_var = tk.BooleanVar(value=False)
        self._pending_show_intersections_var = tk.BooleanVar(value=False)
        self._pending_x_min_var = tk.StringVar(value="-10")
        self._pending_x_max_var = tk.StringVar(value="10")
        self._pending_y_min_var = tk.StringVar()
        self._pending_y_max_var = tk.StringVar()
        self._settings_window: tk.Toplevel | None = None
        self._build_styles()
        self._build_layout()
        self._render(preserve_view=False)

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background="#eef7fb")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("TLabel", background="#eef7fb", foreground="#16384a", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground="#16384a")
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 11), foreground="#214c62")
        style.configure("Muted.TLabel", foreground="#66879a", font=("Segoe UI", 9))
        style.configure("Count.TLabel", foreground="#009bd8", font=("Segoe UI Semibold", 10))
        style.configure("FunctionRow.TFrame", background="#ffffff")
        style.configure("FunctionRow.TLabel", background="#ffffff")
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 9), relief="flat")
        style.configure("Accent.TButton", background="#009bd8", foreground="#ffffff", borderwidth=0)
        style.map(
            "Accent.TButton",
            background=[("active", "#28c5f5"), ("pressed", "#0077b6"), ("disabled", "#a9cfde")],
            foreground=[("disabled", "#eef7fb")],
        )
        style.configure("Info.TButton", font=("Segoe UI Symbol", 12), padding=(6, 4), relief="flat")
        style.configure("Mode.TButton", anchor="w", padding=(14, 12), relief="flat")
        style.configure("Close.TButton", padding=(6, 3))
        style.configure("TEntry", padding=(10, 9), fieldbackground="#ffffff")
        style.configure("TCheckbutton", background="#ffffff")

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=7)
        self.root.columnconfigure(1, weight=3)
        self.root.rowconfigure(0, weight=1)

        graph_pane = ttk.Frame(self.root, style="App.TFrame", padding=(24, 22, 18, 22))
        graph_pane.grid(row=0, column=0, sticky="nsew")
        graph_pane.columnconfigure(0, weight=1)
        graph_pane.rowconfigure(1, weight=1)
        graph_pane.rowconfigure(2, weight=0)

        heading = ttk.Frame(graph_pane, style="App.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        if self._studio_logo is not None:
            self.chart_title = tk.Label(
                heading,
                image=self._studio_logo,
                background="#eef7fb",
                borderwidth=0,
                highlightthickness=0,
            )
            self.chart_title.pack(anchor="w")
        else:
            self.chart_title = ttk.Label(heading, text="GraphiX Studio", style="Title.TLabel")
            self.chart_title.pack(anchor="w")
        self.chart_subtitle = ttk.Label(heading, text="PLANO CARTESIANO", style="Muted.TLabel")
        self.chart_subtitle.pack(anchor="w", pady=(2, 0))

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
        self.toolbar = GraphNavigationToolbar(self.canvas, chart_frame, self._reset_plot_view)
        self.toolbar.update()
        self.toolbar.grid(row=1, column=0, sticky="ew")
        self.cursor_label = ttk.Label(
            graph_pane,
            text="Cursor: mueve sobre el gráfico para leer coordenadas.",
            style="Muted.TLabel",
        )
        self.cursor_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.divider = ttk.Separator(self.root, orient="vertical")
        self.divider.place(relx=0.7, rely=0.04, relheight=0.92, anchor="n")

        self.control_pane = ttk.Frame(self.root, style="App.TFrame", padding=(28, 28, 24, 22))
        self.control_pane.grid(row=0, column=1, sticky="nsew")
        self.control_pane.columnconfigure(0, weight=1)
        self.control_pane.rowconfigure(0, weight=1)
        self.function_pane = ttk.Frame(self.control_pane, style="App.TFrame")
        self.function_pane.grid(row=0, column=0, sticky="nsew")
        self.function_pane.columnconfigure(0, weight=1)
        self.function_pane.rowconfigure(5, weight=1)
        self.function_pane.rowconfigure(7, weight=0)

        self.panel_toggle = tk.Canvas(
            self.root,
            width=42,
            height=42,
            highlightthickness=0,
            cursor="hand2",
        )
        self.panel_toggle.bind("<Button-1>", self._toggle_control_pane)
        self._draw_panel_toggle()
        self.root.bind("<Configure>", self._on_root_configure, add="+")

        self.settings_button = tk.Canvas(
            self.root,
            width=40,
            height=40,
            highlightthickness=0,
            cursor="hand2",
        )
        self.settings_button.bind("<Button-1>", self._open_settings)
        self.settings_button.place(relx=0.985, rely=0.015, anchor="ne")
        self._draw_settings_button()

        self.mode_toggle = tk.Canvas(
            self.root,
            width=42,
            height=42,
            highlightthickness=0,
            cursor="hand2",
        )
        self.mode_toggle.bind("<Button-1>", self._toggle_mode_menu)
        self.mode_toggle.place(x=12, y=12)
        self._draw_mode_toggle()
        self.mode_menu = ttk.Frame(self.root, style="Panel.TFrame", padding=20)
        self.mode_menu.place(relx=0, rely=0, relwidth=0.25, relheight=1)
        self.mode_menu.place_forget()
        self._mode_menu_animation_job: str | None = None
        self._mode_menu_target_visible = False
        self._build_mode_menu()

        ttk.Label(self.function_pane, text="Funciones", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            self.function_pane,
            text="Inserta las funciones que deseas visualizar y gestiona las funciones que se muestran en el plano.",
            style="Muted.TLabel",
            wraplength=600,
        ).grid(row=1, column=0, sticky="w", pady=(4, 22))

        ttk.Label(self.function_pane, text="NUEVA EXPRESIÓN", style="Section.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 8)
        )
        input_row = ttk.Frame(self.function_pane, style="App.TFrame")
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

        list_header = ttk.Frame(self.function_pane, style="App.TFrame")
        list_header.grid(row=4, column=0, sticky="ew", pady=(20, 9))
        list_header.columnconfigure(0, weight=1)
        ttk.Label(list_header, text="LISTA DE FUNCIONES", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.count_label = ttk.Label(list_header, text="0 activas · 0 total", style="Count.TLabel")
        self.count_label.grid(row=0, column=1, sticky="e")

        list_container = ttk.Frame(self.function_pane, style="Panel.TFrame", padding=8)
        list_container.grid(row=5, column=0, sticky="nsew")
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

        self.intersections_header = ttk.Frame(self.function_pane, style="App.TFrame")
        self.intersections_header.grid(row=6, column=0, sticky="ew", pady=(14, 8))
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

        self.intersections_container = ttk.Frame(self.function_pane, style="Panel.TFrame", padding=6)
        self.intersections_container.grid(row=7, column=0, sticky="nsew")
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

        self._build_geometry_manager("Geometría 2D", ("Punto", "Círculo", "Rectángulo"))
        self._build_geometry_manager("Geometría 3D", ("Esfera", "Plano"))
        self.root.tk.call("raise", self.mode_toggle._w)
        self.expression_entry.focus_set()

    def _build_mode_menu(self) -> None:
        header = ttk.Frame(self.mode_menu, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 24))
        ttk.Label(header, text="Espacio de trabajo", style="Title.TLabel").pack(side="left")
        ttk.Button(
            header,
            text="✕",
            style="Close.TButton",
            command=self._hide_mode_menu,
        ).pack(side="right")
        ttk.Label(
            self.mode_menu,
            text="Elige qué deseas visualizar.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 12))
        self._mode_buttons: dict[str, ttk.Button] = {}
        for mode in ("Funciones", "Geometría 2D", "Geometría 3D"):
            button = ttk.Button(
                self.mode_menu,
                text=mode,
                style="Mode.TButton",
                command=lambda selected_mode=mode: self._select_mode(selected_mode),
            )
            button.pack(fill="x", pady=4)
            self._mode_buttons[mode] = button
        self._update_mode_buttons()

    def _build_geometry_manager(self, mode: str, kinds: tuple[str, ...]) -> None:
        pane = ttk.Frame(self.control_pane, style="App.TFrame")
        pane.columnconfigure(0, weight=1)
        pane.rowconfigure(7, weight=1)
        self._geometry_panes[mode] = pane

        title = "Geometría 2D" if mode == "Geometría 2D" else "Geometría 3D"
        ttk.Label(pane, text=title, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        explanation = (
            "Configura e inserta figuras en el plano cartesiano."
            if mode == "Geometría 2D"
            else "Configura e inserta figuras en el espacio tridimensional."
        )
        ttk.Label(
            pane,
            text=explanation,
            style="Muted.TLabel",
            wraplength=600,
        ).grid(row=1, column=0, sticky="w", pady=(4, 18))
        ttk.Label(pane, text="FIGURA", style="Section.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))
        selector = ttk.Combobox(pane, state="readonly", values=kinds)
        selector.current(0)
        selector.grid(row=3, column=0, sticky="ew")
        self._geometry_selectors[mode] = selector
        fields_frame = ttk.Frame(pane, style="App.TFrame")
        fields_frame.grid(row=4, column=0, sticky="ew", pady=(10, 4))
        self._geometry_field_frames[mode] = fields_frame
        selector.bind(
            "<<ComboboxSelected>>",
            lambda _event, selected_mode=mode: self._update_geometry_fields(selected_mode),
        )
        ttk.Button(
            pane,
            text="Insertar figura +",
            style="Accent.TButton",
            command=lambda selected_mode=mode: self._add_geometry(selected_mode),
        ).grid(row=5, column=0, sticky="e", pady=(4, 14))
        list_header = ttk.Frame(pane, style="App.TFrame")
        list_header.grid(row=6, column=0, sticky="ew", pady=(4, 8))
        list_header.columnconfigure(0, weight=1)
        ttk.Label(list_header, text="FIGURAS INSERTADAS", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        count = ttk.Label(list_header, text="0 activas · 0 total", style="Count.TLabel")
        count.grid(row=0, column=1, sticky="e")
        self._geometry_counts[mode] = count
        list_container = ttk.Frame(pane, style="Panel.TFrame", padding=8)
        list_container.grid(row=7, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)
        list_canvas = tk.Canvas(list_container, background="#ffffff", highlightthickness=0)
        list_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=list_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        list_canvas.configure(yscrollcommand=scrollbar.set)
        list_frame = ttk.Frame(list_canvas, style="Panel.TFrame")
        list_frame.columnconfigure(0, weight=1)
        list_window = list_canvas.create_window((0, 0), window=list_frame, anchor="nw")
        list_frame.bind(
            "<Configure>",
            lambda _event, canvas=list_canvas: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        list_canvas.bind(
            "<Configure>",
            lambda event, canvas=list_canvas, window=list_window: canvas.itemconfigure(
                window, width=event.width
            ),
        )
        self._geometry_list_frames[mode] = list_frame
        self._geometry_list_canvases[mode] = list_canvas
        ttk.Label(
            list_frame,
            text="Aún no hay figuras. Selecciona una y configúrala arriba.",
            style="Muted.TLabel",
            padding=(12, 16),
        ).grid(row=0, column=0, sticky="w")
        self._update_geometry_fields(mode)

    def _update_geometry_fields(self, mode: str) -> None:
        field_definitions: dict[str, dict[str, tuple[str, str]]] = {
            "Punto": {"x": ("x", "0"), "y": ("y", "0")},
            "Círculo": {"x": ("Centro x", "0"), "y": ("Centro y", "0"), "r": ("Radio", "3")},
            "Rectángulo": {
                "x": ("Origen x", "-2"),
                "y": ("Origen y", "-1"),
                "width": ("Ancho", "4"),
                "height": ("Alto", "2"),
            },
            "Esfera": {
                "x": ("Centro x", "0"),
                "y": ("Centro y", "0"),
                "z": ("Centro z", "0"),
                "r": ("Radio", "3"),
            },
            "Plano": {"a": ("a (x)", "0"), "b": ("b (y)", "0"), "c": ("c", "0")},
        }
        frame = self._geometry_field_frames[mode]
        for child in frame.winfo_children():
            child.destroy()
        selected_kind = self._geometry_selectors[mode].get()
        entries: dict[str, ttk.Entry] = {}
        for index, (parameter, (label, default)) in enumerate(field_definitions[selected_kind].items()):
            row, column = divmod(index, 2)
            ttk.Label(frame, text=label, style="Muted.TLabel").grid(
                row=row, column=column * 2, sticky="w", padx=(0, 6), pady=4
            )
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, default)
            entry.grid(row=row, column=column * 2 + 1, sticky="ew", padx=(0, 12), pady=4)
            frame.columnconfigure(column * 2 + 1, weight=1)
            entries[parameter] = entry
        self._geometry_fields[mode] = entries

    def _add_geometry(self, mode: str) -> None:
        kind = self._geometry_selectors[mode].get()
        try:
            parameters = {
                name: float(entry.get())
                for name, entry in self._geometry_fields[mode].items()
            }
            if not all(np.isfinite(value) for value in parameters.values()):
                raise ValueError("Todos los parámetros deben ser números finitos.")
            if kind in {"Círculo", "Esfera"} and parameters["r"] <= 0:
                raise ValueError("El radio debe ser mayor que cero.")
            if kind == "Rectángulo" and (
                parameters["width"] <= 0 or parameters["height"] <= 0
            ):
                raise ValueError("El ancho y el alto deben ser mayores que cero.")
        except ValueError as error:
            messagebox.showerror("Parámetros no válidos", str(error), parent=self.root)
            return

        self._geometry_counter += 1
        figure = GeometricFigure(
            identifier=f"{kind} {self._geometry_counter}",
            kind=kind,
            parameters=parameters,
            color=self._PALETTE[(self._geometry_counter - 1) % len(self._PALETTE)],
        )
        self._geometry_items[mode].append(GeometryItem(figure, tk.BooleanVar(value=True), ttk.Frame()))
        self._refresh_geometry_list(mode)
        self._render(preserve_view=True)

    def _refresh_geometry_list(self, mode: str) -> None:
        list_frame = self._geometry_list_frames[mode]
        for child in list_frame.winfo_children():
            child.destroy()
        items = self._geometry_items[mode]
        if not items:
            ttk.Label(
                list_frame,
                text="Aún no hay figuras. Selecciona una y configúrala arriba.",
                style="Muted.TLabel",
                padding=(12, 16),
            ).grid(row=0, column=0, sticky="w")
        for index, item in enumerate(items):
            item.row = ttk.Frame(list_frame, style="FunctionRow.TFrame", padding=(8, 7))
            item.row.grid(row=index, column=0, sticky="ew", pady=2)
            item.row.columnconfigure(2, weight=1)
            ttk.Checkbutton(
                item.row,
                variable=item.selected,
                command=self._render,
            ).grid(row=0, column=0, padx=(0, 8))
            tk.Frame(item.row, width=10, height=10, background=item.figure.color).grid(
                row=0, column=1, sticky="w", padx=(0, 8)
            )
            ttk.Label(
                item.row,
                text=self._format_geometry_label(item.figure),
                style="FunctionRow.TLabel",
                wraplength=320,
            ).grid(row=0, column=2, sticky="w")
            ttk.Button(
                item.row,
                text="Quitar",
                width=8,
                command=lambda current=item, selected_mode=mode: self._remove_geometry(
                    selected_mode, current
                ),
            ).grid(row=0, column=3, padx=(8, 0))
        active_count = sum(item.selected.get() for item in items)
        self._geometry_counts[mode].configure(text=f"{active_count} activas · {len(items)} total")

    @staticmethod
    def _format_geometry_label(figure: GeometricFigure) -> str:
        parameters = ", ".join(
            f"{name}={value:g}" for name, value in figure.parameters.items()
        )
        return f"{figure.identifier} ({parameters})"

    def _remove_geometry(self, mode: str, item: GeometryItem) -> None:
        self._geometry_items[mode].remove(item)
        self._refresh_geometry_list(mode)
        self._render()

    def _draw_mode_toggle(self) -> None:
        background = "#eef7fb" if not self._dark_mode_var.get() else "#101c24"
        foreground = "#16384a" if not self._dark_mode_var.get() else "#dff7ff"
        self.mode_toggle.configure(background=background)
        self.mode_toggle.delete("all")
        if self._menu_icon is not None:
            self.mode_toggle.create_image(21, 21, image=self._menu_icon)
        else:
            self.mode_toggle.create_oval(2, 2, 40, 40, fill=background, outline=foreground, width=1.2)
            for y in (13, 20, 27):
                self.mode_toggle.create_line(13, y, 29, y, fill=foreground, width=2, capstyle=tk.ROUND)

    def _toggle_mode_menu(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self.mode_menu.winfo_ismapped():
            self._hide_mode_menu()
            return
        self._mode_menu_target_visible = True
        self.mode_menu.lift()
        self._animate_mode_menu(opening=True)

    def _hide_mode_menu(self) -> None:
        self._mode_menu_target_visible = False
        self._animate_mode_menu(opening=False)

    def _animate_mode_menu(self, *, opening: bool) -> None:
        if self._mode_menu_animation_job is not None:
            try:
                self.root.after_cancel(self._mode_menu_animation_job)
            except tk.TclError:
                pass
            self._mode_menu_animation_job = None

        width = max(1, int(self.root.winfo_width() * 0.25))
        duration = 220
        start = -width if opening else 0
        end = 0 if opening else -width

        def step(elapsed_ms: int) -> None:
            progress = min(1.0, elapsed_ms / duration)
            eased = 1.0 - (1.0 - progress) ** 3
            x_position = int(start + (end - start) * eased)
            self.mode_menu.place(
                x=x_position,
                y=0,
                width=width,
                height=self.root.winfo_height(),
                relwidth=0,
                relheight=0,
            )

            if progress < 1.0:
                self._mode_menu_animation_job = self.root.after(16, lambda: step(elapsed_ms + 16))
            else:
                self._mode_menu_animation_job = None
                if opening:
                    self.mode_menu.place(x=0, y=0, width=width, height=self.root.winfo_height())
                else:
                    self.mode_menu.place_forget()
                    self.root.tk.call("raise", self.mode_toggle._w)

        if opening:
            self.mode_menu.place(x=start, y=0, width=width, height=self.root.winfo_height())
        else:
            self.mode_menu.place(x=start, y=0, width=width, height=self.root.winfo_height())
        step(0)

    def _update_mode_buttons(self) -> None:
        for mode, button in self._mode_buttons.items():
            button.configure(style="Accent.TButton" if mode == self._mode else "Mode.TButton")

    def _select_mode(self, mode: str) -> None:
        self._mode = mode
        for pane in self._geometry_panes.values():
            pane.grid_remove()
        if mode == "Funciones":
            self.function_pane.grid()
            self.chart_subtitle.configure(text="FUNCIONES")
        else:
            self._geometry_panes[mode].grid(row=0, column=0, sticky="nsew")
            self.chart_subtitle.configure(text=mode.upper())
        self._update_mode_buttons()
        projection = "3d" if mode == "Geometría 3D" else "2d"
        if projection != self._projection:
            self._replace_plot_axes(projection)
        self._hide_mode_menu()
        self._render(preserve_view=False)
        self.root.after_idle(self._stabilize_canvas)

    def _replace_plot_axes(self, projection: str) -> None:
        self.figure.clear()
        self.axes = self.figure.add_subplot(
            111,
            projection="3d" if projection == "3d" else None,
        )
        self._projection = projection
        self.plotter = PlotRenderer(self.figure, self.axes, self.canvas.draw_idle)
        self.toolbar._nav_stack.clear()
        self.toolbar.update()
        self.canvas.mpl_connect("motion_notify_event", self._on_plot_motion)
        self.figure.subplots_adjust(left=0.08, right=0.98, bottom=0.10, top=0.98)
        self.canvas.draw_idle()

    def _stabilize_canvas(self) -> None:
        self.figure.subplots_adjust(left=0.08, right=0.98, bottom=0.10, top=0.98)
        self.canvas.draw_idle()

    def _draw_panel_toggle(self) -> None:
        background = "#eef7fb" if not self._dark_mode_var.get() else "#101c24"
        foreground = "#16384a" if not self._dark_mode_var.get() else "#dff7ff"
        self.panel_toggle.configure(background=background)
        self.panel_toggle.delete("all")
        icon = self._panel_icon_right if self._controls_visible else self._panel_icon_left
        if icon is not None:
            self.panel_toggle.create_image(21, 21, image=icon)
        else:
            self.panel_toggle.create_oval(2, 2, 40, 40, fill=background, outline=foreground, width=1.5)
            arrow = (17, 12, 25, 21, 17, 30) if self._controls_visible else (25, 12, 17, 21, 25, 30)
            self.panel_toggle.create_line(*arrow, fill=foreground, width=2.5, capstyle=tk.ROUND, joinstyle=tk.ROUND)
        self._position_panel_toggle()

    def _position_panel_toggle(self) -> None:
        if self._controls_visible:
            x = self.control_pane.winfo_x() + self.control_pane.winfo_width() - 8
        else:
            x = self.root.winfo_width() - 8
        self.panel_toggle.place(x=x, y=max(0, self.root.winfo_height() - 12), anchor="se")

    def _on_root_configure(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self.root:
            self.root.after_idle(self._position_panel_toggle)

    def _draw_settings_button(self) -> None:
        background = "#eef7fb" if not self._dark_mode_var.get() else "#101c24"
        foreground = "#16384a" if not self._dark_mode_var.get() else "#dff7ff"
        self.settings_button.configure(background=background)
        self.settings_button.delete("all")
        if self._gear_icon is not None:
            self.settings_button.create_image(20, 20, image=self._gear_icon)
        else:
            self.settings_button.create_oval(2, 2, 38, 38, fill=background, outline=foreground, width=1.2)
            self.settings_button.create_text(20, 20, text="⚙", fill=foreground, font=("Segoe UI Symbol", 17))

    def _toggle_control_pane(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._controls_visible = not self._controls_visible
        if self._controls_visible:
            self.root.columnconfigure(0, weight=7)
            self.root.columnconfigure(1, weight=3)
            self.control_pane.grid()
            self.divider.place(relx=0.7, rely=0.04, relheight=0.92, anchor="n")
        else:
            self.control_pane.grid_remove()
            self.root.columnconfigure(0, weight=1)
            self.root.columnconfigure(1, weight=0)
            self.divider.place_forget()
        self._draw_panel_toggle()
        self.root.after_idle(self._position_panel_toggle)

    def _open_settings(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.deiconify()
            self._settings_window.lift()
            return

        self._pending_dark_mode_var.set(self._dark_mode_var.get())
        self._pending_show_intersections_var.set(self.show_intersections_var.get())
        self._pending_x_min_var.set(self.x_min_var.get())
        self._pending_x_max_var.set(self.x_max_var.get())
        self._pending_y_min_var.set(self.y_min_var.get())
        self._pending_y_max_var.set(self.y_max_var.get())

        window = tk.Toplevel(self.root)
        self._settings_window = window
        window.title("Configuración")
        window.transient(self.root)
        window.resizable(False, False)
        window.configure(background="#eef7fb")
        window.protocol("WM_DELETE_WINDOW", self._close_settings)
        content = ttk.Frame(window, style="App.TFrame", padding=22)
        content.grid(sticky="nsew")
        ttk.Label(content, text="Ajustes avanzados", style="Title.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 16)
        )
        ttk.Checkbutton(
            content,
            text="Modo oscuro",
            variable=self._pending_dark_mode_var,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Checkbutton(
            content,
            text="Mostrar intersecciones",
            variable=self._pending_show_intersections_var,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 18))

        ttk.Label(content, text="Intervalo de X", style="Section.TLabel").grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(0, 8)
        )
        self._add_range_inputs(content, 4, self._pending_x_min_var, self._pending_x_max_var)
        ttk.Label(
            content,
            text="Intervalo de Z" if self._mode == "Geometría 3D" else "Intervalo de Y",
            style="Section.TLabel",
        ).grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(18, 4)
        )
        ttk.Label(
            content,
            text="Deja ambos límites vacíos para ajustar automáticamente.",
            style="Muted.TLabel",
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self._add_range_inputs(content, 7, self._pending_y_min_var, self._pending_y_max_var)
        ttk.Button(
            content,
            text="Aplicar",
            style="Accent.TButton",
            command=self._apply_settings,
        ).grid(row=8, column=0, columnspan=4, sticky="e", pady=(20, 0))
        window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - window.winfo_reqwidth()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - window.winfo_reqheight()) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")
        window.grab_set()

    @staticmethod
    def _add_range_inputs(
        parent: ttk.Frame,
        row: int,
        minimum: tk.StringVar,
        maximum: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text="Desde", style="Muted.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(parent, textvariable=minimum, width=12).grid(row=row, column=1, sticky="ew", padx=(0, 16))
        ttk.Label(parent, text="Hasta", style="Muted.TLabel").grid(row=row, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(parent, textvariable=maximum, width=12).grid(row=row, column=3, sticky="ew")

    def _close_settings(self) -> None:
        if self._settings_window is not None:
            self._settings_window.grab_release()
            self._settings_window.destroy()
            self._settings_window = None

    def _apply_settings(self) -> None:
        try:
            x_min = float(self._pending_x_min_var.get())
            x_max = float(self._pending_x_max_var.get())
            if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min >= x_max:
                raise ValueError("El límite inicial de X debe ser menor que el final.")
            y_min = self._pending_y_min_var.get().strip()
            y_max = self._pending_y_max_var.get().strip()
            if bool(y_min) != bool(y_max):
                raise ValueError("Completa ambos límites de Y o deja ambos vacíos.")
            if y_min and y_max:
                parsed_y_min = float(y_min)
                parsed_y_max = float(y_max)
                if (
                    not np.isfinite(parsed_y_min)
                    or not np.isfinite(parsed_y_max)
                    or parsed_y_min >= parsed_y_max
                ):
                    raise ValueError("El límite inferior de Y debe ser menor que el superior.")
        except ValueError as error:
            messagebox.showerror("Intervalo no válido", str(error), parent=self._settings_window or self.root)
            return

        previous_y_limits = self._read_y_limits()
        ranges_changed = (
            (x_min, x_max) != (float(self.x_min_var.get()), float(self.x_max_var.get()))
            or (None if not y_min else (parsed_y_min, parsed_y_max)) != previous_y_limits
        )
        previous_intersections = self.show_intersections_var.get()
        self.x_min_var.set(self._pending_x_min_var.get())
        self.x_max_var.set(self._pending_x_max_var.get())
        self.y_min_var.set(y_min)
        self.y_max_var.set(y_max)
        self._dark_mode_var.set(self._pending_dark_mode_var.get())
        self.show_intersections_var.set(self._pending_show_intersections_var.get())
        if previous_intersections != self.show_intersections_var.get():
            self._toggle_intersections(redraw=False)
        self._apply_theme(redraw=False)
        self._render(preserve_view=not ranges_changed)

    def _apply_theme(self, *, redraw: bool = True) -> None:
        dark = self._dark_mode_var.get()
        colors = {
            "background": "#101c24" if dark else "#eef7fb",
            "panel": "#162d3a" if dark else "#ffffff",
            "foreground": "#dff7ff" if dark else "#16384a",
            "muted": "#96bacb" if dark else "#66879a",
            "section": "#c8efff" if dark else "#214c62",
            "grid": "#294858" if dark else "#dceaf0",
            "axis": "#96bacb" if dark else "#66879a",
            "spine": "#3d6678" if dark else "#c8dae3",
        }
        style = ttk.Style(self.root)
        self.root.configure(background=colors["background"])
        style.configure("App.TFrame", background=colors["background"])
        style.configure("Panel.TFrame", background=colors["panel"])
        style.configure("FunctionRow.TFrame", background=colors["panel"])
        style.configure("FunctionRow.TLabel", background=colors["panel"], foreground=colors["section"])
        style.configure("TLabel", background=colors["background"], foreground=colors["foreground"])
        style.configure("Title.TLabel", foreground=colors["foreground"])
        style.configure("Section.TLabel", foreground=colors["section"])
        style.configure("Muted.TLabel", foreground=colors["muted"])
        style.configure("Count.TLabel", foreground="#56d8ff" if dark else "#009bd8")
        style.configure("TCheckbutton", background=colors["background"], foreground=colors["foreground"])
        style.map(
            "TCheckbutton",
            background=[("active", colors["background"])],
            foreground=[("active", colors["foreground"])],
        )
        style.configure("TEntry", fieldbackground=colors["panel"], foreground=colors["foreground"])
        style.configure("TButton", background=colors["panel"], foreground=colors["foreground"])
        style.configure("Accent.TButton", background="#009bd8", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#28c5f5"), ("pressed", "#0077b6")])
        style.configure(
            "Treeview",
            background=colors["panel"],
            fieldbackground=colors["panel"],
            foreground=colors["foreground"],
        )
        style.configure(
            "Treeview.Heading",
            background=colors["background"],
            foreground=colors["foreground"],
        )
        style.map(
            "Treeview",
            background=[("selected", "#0077b6")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure("TScrollbar", background=colors["panel"], troughcolor=colors["background"])
        self.list_canvas.configure(background=colors["panel"])
        for list_canvas in self._geometry_list_canvases.values():
            list_canvas.configure(background=colors["panel"])
        self.canvas.get_tk_widget().configure(background=colors["panel"])
        self.toolbar.configure(background=colors["background"])
        if isinstance(self.chart_title, tk.Label):
            self.chart_title.configure(background=colors["background"])
        self.figure.set_facecolor(colors["panel"])
        self._draw_settings_button()
        self._draw_mode_toggle()
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.configure(background=colors["background"])
        self._draw_panel_toggle()
        if redraw:
            self._render()

    def _add_expression(self, _event: tk.Event[tk.Misc] | None = None) -> str:
        expression = self.expression_var.get().strip()
        try:
            function = parse_function(expression)
        except ExpressionError as error:
            messagebox.showerror("Expresión no válida", str(error), parent=self.root)
            self.expression_entry.focus_set()
            return "break"

        is_first_function = not self._items
        color = self._PALETTE[len(self._items) % len(self._PALETTE)]
        selected = tk.BooleanVar(value=True)
        row = ttk.Frame(self.list_frame, style="FunctionRow.TFrame", padding=(8, 7))
        identifier = self._next_function_identifier()
        item = FunctionItem(identifier, expression, function, color, selected, row)
        self._items.append(item)
        self._refresh_list()
        self.expression_var.set("")
        self.expression_entry.focus_set()
        self._render(preserve_view=not is_first_function)
        return "break"

    def _reset_plot_view(self) -> None:
        self._render(preserve_view=False)

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
                style="FunctionRow.TLabel",
                font=("Consolas", 11),
            ).grid(row=0, column=2, sticky="w")
            ttk.Button(
                item.row,
                text="ⓘ",
                style="Info.TButton",
                width=5,
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
        window.configure(background="#101c24" if self._dark_mode_var.get() else "#eef7fb")
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
        if self._mode != "Funciones":
            return
        coordinates = self.plotter.on_mouse_move(event)
        if coordinates is None:
            self.cursor_label.configure(text="Cursor: mueve sobre el gráfico para leer coordenadas.")
            return
        self.cursor_label.configure(text=f"Cursor: x = {coordinates[0]:.5g}    y = {coordinates[1]:.5g}")

    def _toggle_intersections(self, *, redraw: bool = True) -> None:
        if self.show_intersections_var.get():
            self.intersections_header.grid()
            self.intersections_container.grid()
            self.intersections_container.master.rowconfigure(5, weight=2)
            self.intersections_container.master.rowconfigure(7, weight=1)
        else:
            self.intersections_header.grid_remove()
            self.intersections_container.grid_remove()
            self.intersections_container.master.rowconfigure(5, weight=1)
            self.intersections_container.master.rowconfigure(7, weight=0)
        if redraw:
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

    def _read_y_limits(self) -> tuple[float, float] | None:
        minimum = self.y_min_var.get().strip()
        maximum = self.y_max_var.get().strip()
        if not minimum and not maximum:
            return None
        if not minimum or not maximum:
            raise ValueError("Ambos límites de Y son necesarios.")
        y_min = float(minimum)
        y_max = float(maximum)
        if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min >= y_max:
            raise ValueError("El límite inferior de Y debe ser menor que el superior.")
        return y_min, y_max

    def _render(self, *, preserve_view: bool = True) -> None:
        try:
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min >= x_max:
                return
            y_limits = self._read_y_limits()
        except ValueError:
            return
        if self._mode == "Geometría 2D":
            figures = [
                item.figure for item in self._geometry_items[self._mode] if item.selected.get()
            ]
            self._geometry_counts[self._mode].configure(
                text=f"{len(figures)} activas · {len(self._geometry_items[self._mode])} total"
            )
            render_geometry_2d(
                self.axes,
                figures,
                (x_min, x_max),
                y_limits,
                dark_mode=self._dark_mode_var.get(),
                preserve_view=preserve_view,
            )
            self.canvas.draw_idle()
            return
        if self._mode == "Geometría 3D":
            figures = [
                item.figure for item in self._geometry_items[self._mode] if item.selected.get()
            ]
            self._geometry_counts[self._mode].configure(
                text=f"{len(figures)} activas · {len(self._geometry_items[self._mode])} total"
            )
            render_geometry_3d(
                self.axes,
                figures,
                (x_min, x_max),
                y_limits,
                dark_mode=self._dark_mode_var.get(),
                preserve_view=preserve_view,
            )
            self.canvas.draw_idle()
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
        self.plotter.render(
            selected,
            x_min,
            x_max,
            self._intersection_points,
            y_limits=y_limits,
            dark_mode=self._dark_mode_var.get(),
            preserve_view=preserve_view,
        )

    def run(self) -> None:
        self.root.mainloop()