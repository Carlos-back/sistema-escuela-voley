"""
Flamingo Sys — Gestión Integral Voley
views/grupos_listado.py — Listado de Grupos (HU01 / KAN-23)
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_label, make_card, make_badge
from services.grupos import listar_grupos
from CTkMessagebox import CTkMessagebox


class GruposListadoView(ctk.CTkFrame):
    """
    Listado de grupos con tabla estilizada.

    Parámetros:
        parent   : frame contenedor
        on_nuevo : callback() para abrir el formulario de alta
    """

    _COL_WIDTHS = {
        "Nombre": 160,
        "Horario": 180,
        "Descripción": 190,
        "Estado": 85,
        "Acciones": 250,
    }

    def __init__(self, parent, rol, on_nuevo, on_editar, on_desactivar, on_reactivar, on_ver):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._rol = (rol or "").lower()
        self._es_admin = self._rol == "administrador"
        self._on_nuevo = on_nuevo
        self._on_editar = on_editar
        self._on_desactivar = on_desactivar
        self._on_reactivar = on_reactivar
        self._on_ver = on_ver
        self.cargar_datos()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

    def cargar_datos(self):
        """Carga todos los grupos (activos e inactivos) desde el backend."""
        self._grupos = listar_grupos(incluir_inactivos=True)

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Encabezado ────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=3, sticky="ew")

        make_label(header, "🏷  Grupos", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Administrá los grupos para clasificar a los alumnos por nivel.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        if self._es_admin:
            make_button(header, text="  ＋  Nuevo Grupo", variant="primary",
                        command=self._on_nuevo,
                        ).grid(row=1, column=2, rowspan=2, padx=28, pady=16)

        # ── Barra de búsqueda + filtro de estado (HU04) ───────
        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))
        search_bar.grid_columnconfigure(0, weight=1)

        self._search_entry = ctk.CTkEntry(
            search_bar, placeholder_text="🔍  Buscar por nombre...",
            font=FONTS.BASE(), height=40, corner_radius=RADIUS.MD,
            border_color=COLORS["border"], fg_color=COLORS["white"],
            text_color=COLORS["text_dark"],
        )
        self._search_entry.grid(row=0, column=0, sticky="ew")
        self._search_entry.bind("<KeyRelease>", lambda e: self._aplicar_filtros())

        self._estado_var = ctk.StringVar(value="Todos")
        ctk.CTkSegmentedButton(
            search_bar, values=["Todos", "Activos", "Inactivos"],
            variable=self._estado_var,
            font=FONTS.BASE(), height=40,
            selected_color=COLORS["primary"], selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["white"], text_color=COLORS["text_dark"],
            command=lambda _v: self._aplicar_filtros(),
        ).grid(row=0, column=1, padx=(12, 0))

        self._stats_label = make_label(
            search_bar, self._texto_contador(), variant="muted")
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
            scrollbar_button_hover_color=COLORS["primary_hover"],
        )
        self._scroll_area.grid(row=1, column=0, sticky="nsew")
        self._scroll_area.grid_columnconfigure(0, weight=1)

        self._aplicar_filtros()

    def _texto_contador(self) -> str:
        activos = sum(1 for g in self._grupos if g.get("estado") == "activo")
        inactivos = len(self._grupos) - activos
        return f"  {activos} activo{'s' if activos != 1 else ''}  ·  {inactivos} inactivo{'s' if inactivos != 1 else ''}"

    def _build_header_row(self, parent):
        hr = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=0)
        hr.grid(row=0, column=0, sticky="ew")
        for i, (col, w) in enumerate(self._COL_WIDTHS.items()):
            cf = ctk.CTkFrame(hr, fg_color="transparent", width=w, height=32)
            cf.grid(row=0, column=i, padx=(20 if i == 0 else 4, 4), pady=5, sticky="w")
            cf.pack_propagate(False)
            make_label(cf, col.upper(), variant="overline", anchor="w"
                       ).pack(side="left", fill="x", expand=True)

    def _aplicar_filtros(self):
        """Filtra por estado y término de búsqueda (HU04). Mantiene el orden por nombre."""
        termino = self._search_entry.get().strip().lower()
        estado_sel = self._estado_var.get()

        filtrados = self._grupos
        if estado_sel == "Activos":
            filtrados = [g for g in filtrados if g.get("estado") == "activo"]
        elif estado_sel == "Inactivos":
            filtrados = [g for g in filtrados if g.get("estado") == "inactivo"]

        if termino:
            filtrados = [g for g in filtrados if termino in g["nombre_grupo"].lower()]

        # Si hay un filtro/búsqueda activa y no hay coincidencias, mensaje específico
        hay_filtro = bool(termino) or estado_sel != "Todos"
        mensaje_vacio = ("Sin resultados para la búsqueda realizada"
                         if hay_filtro else "No hay grupos cargados")
        self._render_rows(filtrados, mensaje_vacio)

    def _render_rows(self, grupos: list, mensaje_vacio: str = "No hay grupos cargados"):
        for widget in self._scroll_area.winfo_children():
            widget.destroy()

        if not grupos:
            make_label(self._scroll_area, mensaje_vacio,
                       variant="muted").grid(row=0, column=0, pady=40)
            return

        for idx, g in enumerate(grupos):
            self._build_data_row(self._scroll_area, idx, g)

    def _build_data_row(self, parent, idx: int, grupo: dict):
        bg = COLORS["white"] if idx % 2 == 0 else "#FAFAFA"
        row_h = 48

        row_f = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        row_f.grid(row=idx, column=0, sticky="ew")

        ctk.CTkFrame(row_f, height=1, fg_color=COLORS["border"],
                     corner_radius=0).place(relx=0, rely=1.0, relwidth=1, y=-1)

        # --- NOMBRE ---
        nf = ctk.CTkFrame(row_f, fg_color="transparent",
                          width=self._COL_WIDTHS["Nombre"], height=row_h)
        nf.grid(row=0, column=0, padx=(20, 4), pady=2, sticky="w")
        nf.pack_propagate(False)
        make_label(nf, grupo["nombre_grupo"], variant="bold", anchor="w"
                   ).pack(side="left", fill="x", expand=True)

        # --- HORARIO ---
        hf = ctk.CTkFrame(row_f, fg_color="transparent",
                          width=self._COL_WIDTHS["Horario"], height=row_h)
        hf.grid(row=0, column=1, padx=4, pady=2, sticky="w")
        hf.pack_propagate(False)
        make_label(hf, grupo["horario"], variant="body", anchor="w"
                   ).pack(side="left", fill="x", expand=True)

        # --- DESCRIPCIÓN ---
        df = ctk.CTkFrame(row_f, fg_color="transparent",
                          width=self._COL_WIDTHS["Descripción"], height=row_h)
        df.grid(row=0, column=2, padx=4, pady=2, sticky="w")
        df.pack_propagate(False)
        make_label(df, grupo.get("descripcion") or "—", variant="muted", anchor="w"
                   ).pack(side="left", fill="x", expand=True)

        # --- ESTADO ---
        sf = ctk.CTkFrame(row_f, fg_color="transparent",
                          width=self._COL_WIDTHS["Estado"], height=row_h)
        sf.grid(row=0, column=3, padx=4, pady=2, sticky="w")
        sf.pack_propagate(False)
        es_activo = grupo.get("estado", "activo") == "activo"
        make_badge(sf, text="Activo" if es_activo else "Inactivo",
                   variant="success" if es_activo else "neutral").pack(side="left")

        # --- ACCIONES (Ver para todos; el resto solo admin, contextual por estado) ---
        af = ctk.CTkFrame(row_f, fg_color="transparent",
                          width=self._COL_WIDTHS["Acciones"], height=row_h)
        af.grid(row=0, column=4, padx=4, pady=2, sticky="w")
        af.pack_propagate(False)

        make_button(af, text="👁 Ver", variant="ghost", size="sm",
                    border_color=COLORS["border"], border_width=1, width=58,
                    text_color=COLORS["text_dark"],
                    command=lambda g=grupo: self._on_ver(g)).pack(side="left", padx=(0, 6))

        if self._es_admin:
            if es_activo:
                make_button(af, text="✏ Editar", variant="ghost", size="sm",
                            border_color=COLORS["primary"], border_width=1, width=72,
                            command=lambda g=grupo: self._on_editar(g)).pack(side="left", padx=(0, 6))
                make_button(af, text="🚫 Baja", variant="ghost", size="sm",
                            border_color=COLORS["error"], border_width=1, width=70,
                            text_color=COLORS["error"],
                            command=lambda g=grupo: self._confirmar_desactivar(g)).pack(side="left")
            else:
                make_button(af, text="♻ Reactivar", variant="ghost", size="sm",
                            border_color=COLORS["success"], border_width=1, width=90,
                            text_color=COLORS["success"],
                            command=lambda g=grupo: self._confirmar_reactivar(g)).pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Confirmaciones (modales)
    # ──────────────────────────────────────────────────────────
    def _confirmar_desactivar(self, grupo: dict):
        msg = CTkMessagebox(
            title="Desactivar grupo",
            message=f"¿Está seguro de desactivar el grupo '{grupo['nombre_grupo']}'?",
            icon="question", option_1="Cancelar", option_2="Desactivar",
            button_color=COLORS["error"], button_hover_color="#C53030",
        )
        if msg.get() == "Desactivar":
            self._on_desactivar(grupo)

    def _confirmar_reactivar(self, grupo: dict):
        msg = CTkMessagebox(
            title="Reactivar grupo",
            message=f"¿Reactivar el grupo '{grupo['nombre_grupo']}'?",
            icon="question", option_1="Cancelar", option_2="Reactivar",
            button_color=COLORS["success"], button_hover_color="#2F855A",
        )
        if msg.get() == "Reactivar":
            self._on_reactivar(grupo)

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def refrescar(self):
        """Recarga los datos y vuelve a pintar la tabla respetando los filtros activos."""
        self.cargar_datos()
        self._stats_label.configure(text=self._texto_contador())
        self._aplicar_filtros()
