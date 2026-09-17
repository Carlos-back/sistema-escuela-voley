"""
Flamingo Sys — Gestión Integral Voley
views/alumnos_listado.py — Listado de Alumnos (HU03 / HU04)
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_label, make_card, make_badge
from services.alumnos import listar_alumnos
from CTkMessagebox import CTkMessagebox


class AlumnosListadoView(ctk.CTkFrame):
    """
    Listado de alumnos con buscador, filtro por estado y acciones por fila.

    Parámetros:
        parent        : frame contenedor
        rol           : rol del usuario en sesión; el alta y las acciones de
                        editar y activar/desactivar solo se muestran al
                        administrador
        on_nuevo      : callback() para abrir el formulario de alta
        on_editar     : callback(alumno) para abrir el formulario de edición
        on_desactivar : callback(alumno) baja lógica
        on_reactivar  : callback(alumno) reactivación
    """

    # 'Alumno' es la columna elástica (weight)
    _COL_BASE = {
        "Alumno": 240,
        "DNI": 120,
        "Grupo": 200,
        "Estado": 100,
    }
    _COL_FLEX = "Alumno"

    _ESTADOS = {"Todos": None, "Activos": "activo", "Inactivos": "inactivo"}

    def __init__(self, parent, rol, on_nuevo, on_editar, on_desactivar, on_reactivar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._rol = (rol or "").lower()
        self._es_admin = self._rol == "administrador"
        self._on_nuevo = on_nuevo
        self._on_editar = on_editar
        self._on_desactivar = on_desactivar
        self._on_reactivar = on_reactivar

        self._col_widths = dict(self._COL_BASE)
        if self._es_admin:
            self._col_widths["Acciones"] = 210

        self._alumnos = []

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
        make_label(header, "🎓  Alumnos", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Registrá alumnos y asignalos a su grupo.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))
        if self._es_admin:
            make_button(header, text="  ＋  Nuevo Alumno", variant="primary",
                        command=self._on_nuevo
                        ).grid(row=1, column=2, rowspan=2, padx=28, pady=16)

        # ── Búsqueda + filtro de estado ───────────────────────
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

        self._estado_var = ctk.StringVar(value="Activos")
        ctk.CTkSegmentedButton(
            search_bar, values=list(self._ESTADOS.keys()),
            variable=self._estado_var,
            font=FONTS.BASE(), height=40,
            selected_color=COLORS["primary"], selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["white"], text_color=COLORS["text_dark"],
            command=lambda _v: self._aplicar_filtros(),
        ).grid(row=0, column=1, padx=(12, 0))

        self._stats_label = make_label(search_bar, "", variant="muted")
        self._stats_label.grid(row=0, column=2, padx=(16, 0))

        # ── Tabla ─────────────────────────────────────────────
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
        return f"  {n} resultado{'s' if n != 1 else ''}"

    def _configurar_columnas(self, contenedor):
        for i, (col, w) in enumerate(self._col_widths.items()):
            contenedor.grid_columnconfigure(
                i, minsize=w, weight=(1 if col == self._COL_FLEX else 0))

    def _build_header_row(self, parent):
        hr = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=0)
        hr.grid(row=0, column=0, sticky="ew")
        self._configurar_columnas(hr)
        for i, col in enumerate(self._col_widths):
            cf = ctk.CTkFrame(hr, fg_color="transparent", height=32)
            cf.grid(row=0, column=i, padx=(20 if i == 0 else 4, 4), pady=5, sticky="ew")
            cf.pack_propagate(False)
            make_label(cf, col.upper(), variant="overline", anchor="w"
                       ).pack(side="left", fill="x", expand=True)

    # ──────────────────────────────────────────────────────────
    # Filtros (HU03)
    # ──────────────────────────────────────────────────────────
    def _aplicar_filtros(self):
        """Consulta el backend con el estado y el texto buscado, y repinta la tabla."""
        termino = self._search_entry.get().strip()
        estado = self._ESTADOS.get(self._estado_var.get())
        self._alumnos = listar_alumnos(filtro_estado=estado, busqueda=termino)
        self._stats_label.configure(text=self._texto_contador())

        hay_filtro = bool(termino) or estado is not None
        mensaje_vacio = ("Sin resultados para la búsqueda realizada"
                         if hay_filtro else "No hay alumnos cargados")
        self._render_rows(self._alumnos, mensaje_vacio)

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

        # Acciones (HU02 / HU04) — solo admin, contextuales según el estado
        if not self._es_admin:
            return
        af = ctk.CTkFrame(row_f, fg_color="transparent", height=row_h)
        af.grid(row=0, column=4, padx=4, pady=2, sticky="ew")
        af.pack_propagate(False)
        if es_activo:
            make_button(af, text="✏ Editar", variant="ghost", size="sm",
                        border_color=COLORS["primary"], border_width=1, width=72,
                        command=lambda a=alumno: self._on_editar(a)).pack(side="left", padx=(0, 6))
            make_button(af, text="🚫 Baja", variant="ghost", size="sm",
                        border_color=COLORS["error"], border_width=1, width=70,
                        text_color=COLORS["error"],
                        command=lambda a=alumno: self._confirmar_desactivar(a)).pack(side="left")
        else:
            make_button(af, text="♻ Reactivar", variant="ghost", size="sm",
                        border_color=COLORS["success"], border_width=1, width=100,
                        text_color=COLORS["success"],
                        command=lambda a=alumno: self._confirmar_reactivar(a)).pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Confirmaciones (modales)
    # ──────────────────────────────────────────────────────────
    def _nombre_de(self, alumno) -> str:
        return f"{alumno.get('nombre','')} {alumno.get('apellido','')}".strip()

    def _confirmar_desactivar(self, alumno: dict):
        msg = CTkMessagebox(
            title="Desactivar alumno",
            message=f"¿Desactivar a {self._nombre_de(alumno)}?\n"
                    "Conserva todos sus datos e historial.",
            icon="question", option_1="Cancelar", option_2="Desactivar",
            button_color=COLORS["error"], button_hover_color="#C53030",
        )
        if msg.get() == "Desactivar":
            self._on_desactivar(alumno)

    def _confirmar_reactivar(self, alumno: dict):
        msg = CTkMessagebox(
            title="Reactivar alumno",
            message=f"¿Reactivar a {self._nombre_de(alumno)}?",
            icon="question", option_1="Cancelar", option_2="Reactivar",
            button_color=COLORS["success"], button_hover_color="#2F855A",
        )
        if msg.get() == "Reactivar":
            self._on_reactivar(alumno)

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def refrescar(self):
        """Recarga los datos respetando el filtro y la búsqueda activos."""
        self._aplicar_filtros()
