"""Responsive Tkinter interface for adding and selecting graph functions."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from graphing.plotter import PlotRenderer, PlotSeries
from utils.reader import ExpressionError, ParsedFunction, parse_function


@dataclass
class FunctionItem:
    expression: str
    function: ParsedFunction
    color: str
    selected: tk.BooleanVar
    row: ttk.Frame


class GraphingApplication:
    """Build and run the complete graphing application window."""

    _PALETTE = ("#137c63", "#d96845", "#3779b7", "#b38222", "#8a5a9e", "#338a91")

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Function Studio | Graficador")
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

        heading = ttk.Frame(graph_pane, style="App.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(heading, text="Function Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="VISUALIZACIÓN CARTESIANA", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))

        chart_frame = ttk.Frame(graph_pane, style="Panel.TFrame", padding=8)
        chart_frame.grid(row=1, column=0, sticky="nsew")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        self.figure = Figure(figsize=(7.5, 6.5), dpi=100, facecolor="#ffffff")
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.plotter = PlotRenderer(self.figure, self.axes, self.canvas.draw_idle)

        divider = ttk.Separator(self.root, orient="vertical")
        divider.place(relx=0.5, rely=0.04, relheight=0.92, anchor="n")

        control_pane = ttk.Frame(self.root, style="App.TFrame", padding=(28, 28, 24, 22))
        control_pane.grid(row=0, column=1, sticky="nsew")
        control_pane.columnconfigure(0, weight=1)
        control_pane.rowconfigure(7, weight=1)

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
        item = FunctionItem(expression, function, color, selected, row)
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
                text=f"f(x) = {item.expression}",
                style="Section.TLabel",
                font=("Consolas", 11),
            ).grid(row=0, column=2, sticky="w")
            ttk.Button(
                item.row,
                text="Quitar",
                width=8,
                command=lambda current=item: self._remove_item(current),
            ).grid(row=0, column=3, padx=(8, 0))
        active_count = sum(item.selected.get() for item in self._items)
        self.count_label.configure(text=f"{active_count} activas · {len(self._items)} total")
        self.list_frame.update_idletasks()
        self._resize_scroll_region()

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
            PlotSeries(f"f(x) = {item.expression}", item.function, item.color)
            for item in self._items
            if item.selected.get()
        ]
        self.count_label.configure(text=f"{len(selected)} activas · {len(self._items)} total")
        self.plotter.render(selected, x_min, x_max)

    def run(self) -> None:
        self.root.mainloop()