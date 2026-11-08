"""
Flamingo Sys — Gestión Integral Voley
views/informe_ocupacion.py — Informe de ocupación de grupos por período (Sprint 5, HU04)
"""

import datetime
from tkinter import filedialog

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from theme import COLORS, FONTS, RADIUS, make_badge, make_button, make_card, make_label
from services import inscripciones as insc_service


class InformeOcupacionView(ctk.CTkFrame):
    """
    Informe para el administrador: por cada grupo, cupo, inscriptos, lugares
    libres, % de ocupación y estado (Disponible / Casi completo / Completo),
    con fila de totales; movimientos del período (altas y anulaciones) y
    anulaciones agrupadas por motivo. Se exporta a PDF.
    """

    _COLUMNAS = (("Grupo", 150), ("Horario", 190), ("Cupo", 60), ("Inscriptos", 85),
                 ("Libres", 60), ("Ocupación", 150), ("Estado", 120),
                 ("Altas", 60), ("Anuladas", 75))
    _BADGE = {"Completo": "error", "Casi completo": "warning", "Disponible": "success"}

    def __init__(self, parent, usuario):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._usuario = usuario
        self._informe = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=3, sticky="ew")
        make_label(header, "📊  Informe de ocupación", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Ocupación de cada grupo, altas y anulaciones del período.",
                   variant="muted").grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))
        self._pdf_btn = make_button(header, text="  ⬇  Exportar a PDF", variant="primary",
                                    command=self._exportar_pdf)
        self._pdf_btn.grid(row=1, column=2, rowspan=2, padx=28, pady=16)

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))
        make_label(barra, "Período", variant="label").pack(side="left", padx=(0, 6))
        self._periodo_var = ctk.StringVar(value=str(insc_service.anio_actual()))
        self._periodo_menu = ctk.CTkOptionMenu(
            barra, variable=self._periodo_var, values=[self._periodo_var.get()], width=110,
            font=FONTS.BASE(), height=36, corner_radius=RADIUS.MD,
            fg_color=COLORS["white"], button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"], text_color=COLORS["text_dark"],
            dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"])
        self._periodo_menu.pack(side="left", padx=(0, 12))
        make_button(barra, text="Generar informe", variant="secondary",
                    command=self.generar).pack(side="left")
        self._resumen = make_label(barra, "", variant="muted")
        self._resumen.pack(side="left", padx=(16, 0))

        self._body = ctk.CTkScrollableFrame(
            self, fg_color=COLORS["bg"], corner_radius=0,
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_hover"])
        self._body.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self._body.grid_columnconfigure(0, weight=1)

    # ──────────────────────────────────────────────────────────
    # Render
    # ──────────────────────────────────────────────────────────
    def generar(self):
        """Calcula el informe del período elegido y lo dibuja."""
        self._informe = insc_service.informe_ocupacion(int(self._periodo_var.get()))
        for w in self._body.winfo_children():
            w.destroy()

        if not self._informe or not self._informe["hay_datos"]:
            self._pdf_btn.configure(state="disabled", fg_color="#CCCCCC")
            self._resumen.configure(text="")
            card = make_card(self._body)
            card.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
            make_label(card, "No hay inscripciones para el período seleccionado",
                       variant="muted").pack(pady=40)
            return

        self._pdf_btn.configure(state="normal", fg_color=COLORS["primary"])
        t = self._informe["totales"]
        self._resumen.configure(
            text=f"Ocupación general {t['porcentaje']}% · {t['vigentes']} de {t['cupo']} lugares")

        self._render_tarjetas(t)
        self._render_tabla()
        self._render_motivos()

    def _render_tarjetas(self, t):
        fila = ctk.CTkFrame(self._body, fg_color="transparent")
        fila.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        datos = [("Ocupación general", f"{t['porcentaje']}%", COLORS["primary"]),
                 ("Inscriptos", f"{t['vigentes']} / {t['cupo']}", COLORS["text_dark"]),
                 ("Lugares libres", str(t["libres"]), COLORS["success"]),
                 ("Altas del período", str(t["altas"]), COLORS["info"]),
                 ("Anulaciones", str(t["anuladas"]), COLORS["error"])]
        for i, (titulo, valor, color) in enumerate(datos):
            fila.grid_columnconfigure(i, weight=1, uniform="tarjeta")
            card = make_card(fila)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            make_label(card, titulo.upper(), variant="overline").pack(anchor="w", padx=16,
                                                                      pady=(12, 0))
            make_label(card, valor, variant="h2", text_color=color).pack(anchor="w", padx=16,
                                                                         pady=(0, 12))

    def _render_tabla(self):
        card = make_card(self._body)
        card.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        card.grid_columnconfigure(0, weight=1)
        make_label(card, "Ocupación por grupo", variant="h3"
                   ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 8))

        filas = list(self._informe["grupos"])
        t = self._informe["totales"]
        total = {"nombre_grupo": "Total", "horario": "", "cupo": t["cupo"],
                 "vigentes": t["vigentes"], "libres": t["libres"],
                 "porcentaje": t["porcentaje"], "estado": None,
                 "altas": t["altas"], "anuladas": t["anuladas"]}

        self._fila_tabla(card, 1, [c for c, _ in self._COLUMNAS], encabezado=True)
        for i, g in enumerate(filas + [total], start=2):
            self._fila_tabla(card, i, g, es_total=g is total)

    def _fila_tabla(self, parent, row, datos, encabezado=False, es_total=False):
        bg = "#F8FAFC" if encabezado else (COLORS["primary_light"] if es_total else
                                           (COLORS["white"] if row % 2 else "#FAFAFA"))
        f = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        f.grid(row=row, column=0, sticky="ew", padx=1, pady=(0, 16 if es_total else 0))
        for i, (_col, ancho) in enumerate(self._COLUMNAS):
            f.grid_columnconfigure(i, minsize=ancho, weight=1 if i == 1 else 0)

        if encabezado:
            for i, col in enumerate(datos):
                make_label(f, col.upper(), variant="overline", anchor="w"
                           ).grid(row=0, column=i, sticky="w", padx=(20 if i == 0 else 6, 6),
                                  pady=8)
            return

        variante = "bold" if es_total else "body"
        valores = [datos["nombre_grupo"], datos["horario"], datos["cupo"], datos["vigentes"],
                   datos["libres"]]
        for i, v in enumerate(valores):
            make_label(f, str(v), variant=variante if i != 1 else "muted", anchor="w"
                       ).grid(row=0, column=i, sticky="w", padx=(20 if i == 0 else 6, 6),
                              pady=10)

        # Barra de ocupación
        barra = ctk.CTkFrame(f, fg_color="transparent")
        barra.grid(row=0, column=5, sticky="w", padx=6)
        pct = datos["porcentaje"]
        color = (COLORS["error"] if pct >= 100 else
                 COLORS["warning"] if pct >= insc_service.UMBRAL_CASI_COMPLETO else
                 COLORS["success"])
        progreso = ctk.CTkProgressBar(barra, width=80, height=8, progress_color=color,
                                      fg_color=COLORS["border"])
        progreso.set(min(pct / 100, 1))
        progreso.pack(side="left")
        make_label(barra, f" {pct}%", variant=variante).pack(side="left")

        if datos["estado"]:
            make_badge(f, datos["estado"], self._BADGE[datos["estado"]]
                       ).grid(row=0, column=6, sticky="w", padx=6)
        make_label(f, str(datos["altas"]), variant=variante
                   ).grid(row=0, column=7, sticky="w", padx=6)
        make_label(f, str(datos["anuladas"]), variant=variante,
                   text_color=COLORS["error"] if datos["anuladas"] else COLORS["text_dark"]
                   ).grid(row=0, column=8, sticky="w", padx=6)

    def _render_motivos(self):
        card = make_card(self._body)
        card.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        make_label(card, "Anulaciones por motivo", variant="h3"
                   ).pack(anchor="w", padx=20, pady=(16, 8))
        motivos = self._informe["motivos"]
        if not motivos:
            make_label(card, "No hubo anulaciones en el período.", variant="muted"
                       ).pack(anchor="w", padx=20, pady=(0, 16))
            return
        maximo = max(m["cantidad"] for m in motivos)
        for m in motivos:
            fila = ctk.CTkFrame(card, fg_color="transparent")
            fila.pack(fill="x", padx=20, pady=3)
            make_label(fila, m["motivo"], variant="body", width=180, anchor="w"
                       ).pack(side="left")
            barra = ctk.CTkProgressBar(fila, width=240, height=10,
                                       progress_color=COLORS["error"],
                                       fg_color=COLORS["border"])
            barra.set(m["cantidad"] / maximo)
            barra.pack(side="left", padx=8)
            make_label(fila, str(m["cantidad"]), variant="bold").pack(side="left")
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

    # ──────────────────────────────────────────────────────────
    # Exportación
    # ──────────────────────────────────────────────────────────
    def _exportar_pdf(self):
        if not self._informe or not self._informe["hay_datos"]:
            return
        nombre = (f"informe_ocupacion_{self._informe['periodo']}_"
                  f"{datetime.date.today():%Y%m%d}.pdf")
        path = filedialog.asksaveasfilename(
            title="Exportar informe", defaultextension=".pdf", initialfile=nombre,
            filetypes=[("Documento PDF", "*.pdf")])
        if not path:
            return
        exito, mensaje = insc_service.exportar_informe_pdf(path, self._informe, self._usuario)
        CTkMessagebox(title="Exportar a PDF" if exito else "Atención",
                      message=f"{mensaje}\n{path}" if exito else mensaje,
                      icon="check" if exito else "warning", option_1="OK")

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def refrescar(self):
        periodos = [str(p) for p in insc_service.periodos_registrados()]
        self._periodo_menu.configure(values=periodos)
        if self._periodo_var.get() not in periodos:
            self._periodo_var.set(str(insc_service.anio_actual()))
        self.generar()
