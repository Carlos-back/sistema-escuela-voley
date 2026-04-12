"""
Flamingo Sys — Gestión Integral Voley
views/dashboard.py — Panel principal (dashboard)
"""

import customtkinter as ctk
from datetime import datetime
from theme import COLORS, FONTS, RADIUS, make_button, make_label, make_card, make_badge
from services.dashboard import obtener_resumen_dashboard, obtener_proximas_clases, obtener_ingresos_mensuales

try:
    import matplotlib
    import matplotlib.ticker
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False


class DashboardView(ctk.CTkFrame):
    """
    Dashboard principal post-login.

    Parámetros:
        parent : frame contenedor
        user   : dict con datos del usuario actual
    """

    def __init__(self, parent, user: dict):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._user = user or {}
        self._stats = obtener_resumen_dashboard()
        self._clases = obtener_proximas_clases()
        self._ingresos_mensuales = obtener_ingresos_mensuales()
        
        # MOCK de actividad para visualización (esto podría venir de logs en una versión futura)
        self._actividad = [
            {"hora": "09:15", "texto": "Nuevo alumno inscripto: Valentina Ruiz",    "tipo": "alumno"},
            {"hora": "10:30", "texto": "Pago recibido: $5.000 — Lucas Pérez",        "tipo": "pago"},
            {"hora": "11:00", "texto": "Clase de Avanzadas — Prof. García",          "tipo": "clase"},
        ]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=3, sticky="ew")

        nombre = self._user.get("nombre", "Usuario")
        rol    = self._user.get("rol", "").capitalize()
        hora   = datetime.now().strftime("%H:%M")
        fecha  = datetime.now().strftime("%A %d de %B de %Y").capitalize()

        make_label(header, f"{self._get_saludo()}, {nombre}! 👋",
                   variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(18, 2))

        make_label(header, f"Rol: {rol}   ·   {fecha}   ·   {hora}",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 18))

        ctk.CTkLabel(header, text="🏐",
                     font=FONTS.XXXL()).grid(row=1, column=2, rowspan=2, padx=28)

        # ── Body scrollable ───────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # ── KPI cards ─────────────────────────────────────────
        kpis = [
            ("👩‍🎓", "Alumnos Activos",
             str(self._stats.get("total_alumnos", 0)),
             "Total registrados",
             COLORS["primary"]),
            ("💳", "Recaudación Semanal",
             f"${self._stats.get('recaudacion_semanal', 0):,.0f}".replace(",", "."),
             "Últimos 7 días",
             COLORS["success"]),
            ("📅", "Presentes Semanal",
             str(self._stats.get("asistencias_semanales", 0)),
             "Total asistencias",
             "#8B5CF6"),
            ("🕐", "Última Actualización",
             self._stats.get("fecha_actualización", "--/--"),
             "Sincronizado",
             COLORS["info"]),
        ]
        for i, (icon, titulo, valor, sub, color) in enumerate(kpis):
            self._make_kpi_card(body, row=0, col=i,
                                icon=icon, titulo=titulo,
                                valor=valor, sub=sub, color=color)

        body.grid_rowconfigure(1, weight=1)

        # ── Gráfico ───────────────────────────────────────────
        chart_frame = make_card(body)
        chart_frame.grid(row=1, column=0, columnspan=3,
                         sticky="nsew", padx=(12, 6), pady=12)
        chart_frame.grid_columnconfigure(0, weight=1)
        chart_frame.grid_rowconfigure(1, weight=1)

        make_label(chart_frame, "📈  Ingresos mensuales", variant="bold"
                   ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 0))

        self._build_chart(chart_frame)

        # ── Actividad reciente ────────────────────────────────
        activity_frame = make_card(body)
        activity_frame.grid(row=1, column=3, sticky="nsew", padx=(6, 12), pady=12)
        activity_frame.grid_columnconfigure(0, weight=1)

        make_label(activity_frame, "🕐  Actividad reciente", variant="bold"
                   ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 8))

        tipo_colors = {
            "alumno":  ("#ECFDF5", "#059669"),
            "pago":    ("#EFF6FF", "#2563EB"),
            "clase":   ("#F5F3FF", "#7C3AED"),
            "alerta":  ("#FEF3C7", "#D97706"),
            "usuario": ("#FDF2F8", "#BE185D"),
        }
        for idx, item in enumerate(self._actividad):
            bg, fg = tipo_colors.get(item["tipo"], ("#F5F5F5", "#374151"))
            row_f = ctk.CTkFrame(activity_frame, fg_color=bg, corner_radius=8)
            row_f.grid(row=idx + 1, column=0, sticky="ew", padx=14, pady=3)
            row_f.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row_f, text=item["hora"],
                         font=FONTS.XS(), text_color=fg, width=36,
                         ).grid(row=0, column=0, padx=(10, 6), pady=8)
            ctk.CTkLabel(row_f, text=item["texto"],
                         font=FONTS.SM(), text_color="#374151",
                         anchor="w", wraplength=160, justify="left",
                         ).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=8)

        ctk.CTkLabel(activity_frame, text="", height=10).grid(
            row=len(self._actividad) + 1, column=0)

        # ── Accesos rápidos ───────────────────────────────────
        quick = ctk.CTkFrame(body, fg_color="transparent")
        quick.grid(row=2, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 16))
        quick.grid_columnconfigure((0, 1, 2, 3), weight=1)

        make_label(quick, "Accesos rápidos", variant="overline"
                   ).grid(row=0, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 8))

        accesos = [
            ("➕  Nuevo Alumno",   "primary"),
            ("💳  Registrar Pago", "success"),
            ("📋  Ver Listados",   "info"),
            ("📊  Reportes",       "warning"),
        ]
        for i, (texto, variant) in enumerate(accesos):
            make_button(quick, text=texto, variant=variant,
                        command=lambda: None,  # TODO: conectar con backend
                        ).grid(row=1, column=i, sticky="ew", padx=4)

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────
    def _make_kpi_card(self, parent, row, col, icon, titulo, valor, sub, color):
        card = make_card(parent)
        card.grid(row=row, column=col, sticky="nsew",
                  padx=(12 if col == 0 else 6, 12 if col == 3 else 6), pady=12)
        card.grid_columnconfigure(0, weight=1)

        # Barra de color lateral
        ctk.CTkFrame(card, width=4, fg_color=color, corner_radius=2
                     ).place(relx=0, rely=0.1, relheight=0.8, x=10)

        ctk.CTkLabel(card, text=icon, font=FONTS.XXXL()
                     ).grid(row=0, column=0, sticky="w", padx=(22, 0), pady=(16, 0))
        ctk.CTkLabel(card, text=valor, font=FONTS.XXXL_BOLD(), text_color=color
                     ).grid(row=1, column=0, sticky="w", padx=(22, 0))
        make_label(card, titulo, variant="bold"
                   ).grid(row=2, column=0, sticky="w", padx=(22, 0))
        make_label(card, sub, variant="caption"
                   ).grid(row=3, column=0, sticky="w", padx=(22, 0), pady=(0, 14))

    def _build_chart(self, parent):
        if not MATPLOTLIB_OK:
            make_label(parent, "⚠  Instalá matplotlib para ver el gráfico",
                       variant="muted").grid(row=1, column=0, pady=40)
            return

        datos = self._ingresos_mensuales
        fig = Figure(figsize=(5.5, 2.8), dpi=100, facecolor="#FFFFFF")
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#FAFAFA")

        x = range(len(datos["labels"]))
        barras = ax.bar(x, datos["valores"], color=COLORS["primary"],
                        alpha=0.85, width=0.55, zorder=2)
        barras[-1].set_color(COLORS["primary_hover"])
        barras[-1].set_alpha(1.0)

        ax.set_xticks(list(x))
        ax.set_xticklabels(datos["labels"], fontsize=10)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda val, _: f"${val/1000:.0f}K")
        )
        ax.tick_params(axis="y", labelsize=9)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(COLORS["border"])
        ax.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
        ax.set_axisbelow(True)

        for bar, val in zip(barras, datos["valores"]):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 1000,
                    f"${val/1000:.0f}K",
                    ha="center", va="bottom", fontsize=9, color="#374151")

        fig.tight_layout(pad=1.2)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew",
                                    padx=16, pady=(8, 16))

    def _get_saludo(self) -> str:
        h = datetime.now().hour
        return "¡Buenos días" if h < 12 else "¡Buenas tardes" if h < 19 else "¡Buenas noches"
