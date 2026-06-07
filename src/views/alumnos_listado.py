"""
Flamingo Sys — Gestión Integral Voley
views/alumnos_listado.py — Listado de Alumnos
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_label, make_card, make_badge
from services.alumnos import listar_alumnos


class AlumnosListadoView(ctk.CTkFrame):
    """
    Listado de alumnos activos con buscador y alta.

    Parámetros:
        parent   : frame contenedor
        on_nuevo : callback() para abrir el formulario de alta
    """

    # 'Alumno' es la columna elástica (weight)
    _COL_WIDTHS = {
        "Alumno": 240,
        "DNI": 120,
        "Grupo": 200,
        "Estado": 100,
    }
    _COL_FLEX = "Alumno"

    def __init__(self, parent, on_nuevo):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_nuevo = on_nuevo
        self.cargar_datos()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

    def cargar_datos(self):
        """Carga los alumnos activos desde el backend."""
        self._alumnos = listar_alumnos()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=3, sticky="ew")
        make_label(header, "🎓  Alumnos", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Registrá alumnos y asignalos a su grupo.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))
        make_button(header, text="  ＋  Nuevo Alumno", variant="primary",
                    command=self._on_nuevo
                    ).grid(row=1, column=2, rowspan=2, padx=28, pady=16)

        # Barra de búsqueda
        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))
        search_bar.grid_columnconfigure(0, weight=1)
        self._search_entry = ctk.CTkEntry(
            search_bar, placeholder_text="🔍  Buscar por nombre, apellido o DNI...",
            font=FONTS.BASE(), height=40, corner_radius=RADIUS.MD,
            border_color=COLORS["border"], fg_color=COLORS["white"],
            text_color=COLORS["text_dark"])
        self._search_entry.grid(row=0, column=0, sticky="ew")
        self._search_entry.bind("<KeyRelease>", lambda e: self._aplicar_filtros())
        self._stats_label = make_label(search_bar, self._texto_contador(), variant="muted")
        self._stats_label.grid(row=0, column=1, padx=(16, 0))

        # Tabla
        tabla_wrapper = make_card(self)
        tabla_wrapper.grid(row=2, column=0, sticky="nsew", padx=20, pady=12)
        tabla_wrapper.grid_columnconfigure(0, weight=1)
        tabla_wrapper.grid_rowconfigure(1, weight=1)
        self._build_header_row(tabla_wrapper)
        self._scroll_area = ctk.CTkScrollableFrame(
            tabla_wrapper, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_hover"])
        self._scroll_area.grid(row=1, column=0, sticky="nsew")
        self._scroll_area.grid_columnconfigure(0, weight=1)
        self._aplicar_filtros()

    def _texto_contador(self) -> str:
        n = len(self._alumnos)
        return f"  {n} alumno{'s' if n != 1 else ''} activo{'s' if n != 1 else ''}"

    def _configurar_columnas(self, contenedor):
        for i, (col, w) in enumerate(self._COL_WIDTHS.items()):
            contenedor.grid_columnconfigure(
                i, minsize=w, weight=(1 if col == self._COL_FLEX else 0))

    def _build_header_row(self, parent):
        hr = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=0)
        hr.grid(row=0, column=0, sticky="ew")
        self._configurar_columnas(hr)
        for i, col in enumerate(self._COL_WIDTHS):
            cf = ctk.CTkFrame(hr, fg_color="transparent", height=32)
            cf.grid(row=0, column=i, padx=(20 if i == 0 else 4, 4), pady=5, sticky="ew")
            cf.pack_propagate(False)
            make_label(cf, col.upper(), variant="overline", anchor="w"
                       ).pack(side="left", fill="x", expand=True)

    def _aplicar_filtros(self):
        termino = self._search_entry.get().strip().lower()
        if termino:
            filtrados = [
                a for a in self._alumnos
                if termino in f"{a.get('nombre','')} {a.get('apellido','')}".lower()
                or termino in str(a.get("dni", "")).lower()
            ]
        else:
            filtrados = self._alumnos
        mensaje_vacio = ("Sin resultados para la búsqueda realizada"
                         if termino else "No hay alumnos cargados")
        self._render_rows(filtrados, mensaje_vacio)

    def _render_rows(self, alumnos, mensaje_vacio="No hay alumnos cargados"):
        for widget in self._scroll_area.winfo_children():
            widget.destroy()
        if not alumnos:
            make_label(self._scroll_area, mensaje_vacio, variant="muted"
                       ).grid(row=0, column=0, pady=40)
            return
        for idx, a in enumerate(alumnos):
            self._build_data_row(self._scroll_area, idx, a)

    def _build_data_row(self, parent, idx, alumno):
        bg = COLORS["white"] if idx % 2 == 0 else "#FAFAFA"
        row_h = 48
        row_f = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        row_f.grid(row=idx, column=0, sticky="ew")
        self._configurar_columnas(row_f)
        ctk.CTkFrame(row_f, height=1, fg_color=COLORS["border"],
                     corner_radius=0).place(relx=0, rely=1.0, relwidth=1, y=-1)

        # Alumno (nombre + apellido)
        nf = ctk.CTkFrame(row_f, fg_color="transparent", height=row_h)
        nf.grid(row=0, column=0, padx=(20, 4), pady=2, sticky="ew")
        nf.pack_propagate(False)
        nombre_completo = f"{alumno.get('nombre','')} {alumno.get('apellido','')}".strip()
        make_label(nf, nombre_completo or "—", variant="bold", anchor="w"
                   ).pack(side="left", fill="x", expand=True)

        # DNI
        df = ctk.CTkFrame(row_f, fg_color="transparent", height=row_h)
        df.grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        df.pack_propagate(False)
        make_label(df, str(alumno.get("dni", "—")), variant="body", anchor="w"
                   ).pack(side="left", fill="x", expand=True)

        # Grupo
        gf = ctk.CTkFrame(row_f, fg_color="transparent", height=row_h)
        gf.grid(row=0, column=2, padx=4, pady=2, sticky="ew")
        gf.pack_propagate(False)
        make_label(gf, alumno.get("nombre_grupo") or "—", variant="muted", anchor="w"
                   ).pack(side="left", fill="x", expand=True)

        # Estado
        sf = ctk.CTkFrame(row_f, fg_color="transparent", height=row_h)
        sf.grid(row=0, column=3, padx=4, pady=2, sticky="ew")
        sf.pack_propagate(False)
        es_activo = alumno.get("estado", "activo") == "activo"
        make_badge(sf, text="Activo" if es_activo else "Inactivo",
                   variant="success" if es_activo else "neutral").pack(side="left")

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def refrescar(self):
        self.cargar_datos()
        self._stats_label.configure(text=self._texto_contador())
        self._aplicar_filtros()
