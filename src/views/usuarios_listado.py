"""
Flamingo Sys — Gestión Integral Voley
views/usuarios_listado.py — Gestión de Usuarios (listado)
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_label, make_card, make_badge, make_divider


class UsuariosListadoView(ctk.CTkFrame):
    """
    Listado de usuarios con tabla estilizada y buscador.

    Parámetros:
        parent    : frame contenedor
        on_nuevo  : callback() para abrir formulario nuevo usuario
        on_editar : callback(usuario_dict) para abrir formulario edición
    """

    # TODO: conectar con backend — obtener usuarios reales de BD
    _MOCK_USUARIOS = [
        {"dni": "12345678", "nombre": "Lautaro Recio",    "email": "reciolauti@gmail.com",   "rol": "Administrador", "activo": True},
        {"dni": "87654321", "nombre": "Carlos Mendez",   "email": "carlos@flamingo.com",  "rol": "Profesor",      "activo": True},
        {"dni": "11223344", "nombre": "Valentina López", "email": "vale@flamingo.com",    "rol": "Profesor",      "activo": True},
        {"dni": "55667788", "nombre": "Martín Suárez",   "email": "martin@flamingo.com",  "rol": "Profesor",      "activo": False},
        {"dni": "99887766", "nombre": "Sofía Ramírez",   "email": "sofia@flamingo.com",   "rol": "Administrador", "activo": True},
        {"dni": "44332211", "nombre": "Diego Torres",    "email": "diego@flamingo.com",   "rol": "Profesor",      "activo": False},
    ]

    # Estos anchos definen el esqueleto de la tabla
    _COL_WIDTHS = {
        "DNI": 100, 
        "Nombre": 220, 
        "Email": 240,
        "Rol": 130, 
        "Estado": 100, 
        "Acciones": 120,
    }

    def __init__(self, parent, on_nuevo, on_editar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_nuevo = on_nuevo
        self._on_editar = on_editar
        self._usuarios = [dict(u) for u in self._MOCK_USUARIOS]

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

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

        make_label(header, "👥  Gestión de Usuarios", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Administrá los usuarios del sistema y sus permisos de acceso.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        make_button(header, text="  ＋  Nuevo Usuario", variant="primary",
                    command=self._on_nuevo,
                    ).grid(row=1, column=2, rowspan=2, padx=28, pady=16)

        # ── Barra de búsqueda ─────────────────────────────────
        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))
        search_bar.grid_columnconfigure(0, weight=1)

        row_s = ctk.CTkFrame(search_bar, fg_color="transparent")
        row_s.grid(row=0, column=0, sticky="ew")
        row_s.grid_columnconfigure(0, weight=1)

        self._search_entry = ctk.CTkEntry(
            row_s,
            placeholder_text="🔍  Buscar por nombre o DNI...",
            font=FONTS.BASE(), height=40, corner_radius=RADIUS.MD,
            border_color=COLORS["border"], fg_color=COLORS["white"],
            text_color=COLORS["text_dark"],
        )
        self._search_entry.grid(row=0, column=0, sticky="ew")
        self._search_entry.bind("<KeyRelease>", self._filtrar)

        total   = len(self._usuarios)
        activos = sum(1 for u in self._usuarios if u["activo"])
        self._stats_label = make_label(
            row_s, f"  {total} usuarios  ·  {activos} activos", variant="muted")
        self._stats_label.grid(row=0, column=1, padx=(16, 0))

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

        self._render_rows(self._usuarios)

    def _build_header_row(self, parent):
        """Crea la fila de títulos con marcos de ancho fijo para alineación total."""
        hr = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=0)
        hr.grid(row=0, column=0, sticky="ew")

        for i, (col, w) in enumerate(self._COL_WIDTHS.items()):
            # Definimos alto explícito para el encabezado
            cf = ctk.CTkFrame(hr, fg_color="transparent", width=w, height=32)
            cf.grid(row=0, column=i, padx=(20 if i == 0 else 4, 4), pady=5, sticky="w")
            cf.pack_propagate(False)
            
            make_label(cf, col.upper(), variant="overline", anchor="w").pack(side="left", fill="x", expand=True)

    def _render_rows(self, usuarios: list):
        for widget in self._scroll_area.winfo_children():
            widget.destroy()

        if not usuarios:
            make_label(self._scroll_area, "No se encontraron usuarios",
                       variant="muted").grid(row=0, column=0, pady=40)
            return

        for idx, u in enumerate(usuarios):
            self._build_data_row(self._scroll_area, idx, u)

    def _build_data_row(self, parent, idx: int, usuario: dict):
        bg = COLORS["white"] if idx % 2 == 0 else "#FAFAFA"
        row_h = 48  # Altura fija para todas las celdas de la fila

        row_f = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0)
        row_f.grid(row=idx, column=0, sticky="ew")

        # Línea divisoria inferior
        ctk.CTkFrame(row_f, height=1, fg_color=COLORS["border"],
                     corner_radius=0).place(relx=0, rely=1.0, relwidth=1, y=-1)

        col_idx = 0

        # --- DNI ---
        df = ctk.CTkFrame(row_f, fg_color="transparent", width=self._COL_WIDTHS["DNI"], height=row_h)
        df.grid(row=0, column=col_idx, padx=(20, 4), pady=2, sticky="w")
        df.pack_propagate(False)
        make_label(df, usuario["dni"], variant="bold", anchor="w").pack(side="left", fill="x", expand=True)
        col_idx += 1

        # --- NOMBRE (con avatar) ---
        nf = ctk.CTkFrame(row_f, fg_color="transparent", width=self._COL_WIDTHS["Nombre"], height=row_h)
        nf.grid(row=0, column=col_idx, padx=4, pady=2, sticky="w")
        nf.pack_propagate(False)
        
        av = ctk.CTkFrame(nf, width=28, height=28, corner_radius=14, fg_color=COLORS["primary"])
        av.pack(side="left", padx=(0, 8))
        av.pack_propagate(False)
        ctk.CTkLabel(av, text=usuario["nombre"][0].upper(),
                     font=FONTS.SM_BOLD(), text_color="white",
                     ).place(relx=0.5, rely=0.5, anchor="center")
        
        make_label(nf, usuario["nombre"], variant="body", anchor="w").pack(side="left", fill="x", expand=True)
        col_idx += 1

        # --- EMAIL ---
        ef = ctk.CTkFrame(row_f, fg_color="transparent", width=self._COL_WIDTHS["Email"], height=row_h)
        ef.grid(row=0, column=col_idx, padx=4, pady=2, sticky="w")
        ef.pack_propagate(False)
        make_label(ef, usuario["email"], variant="muted", anchor="w").pack(side="left", fill="x", expand=True)
        col_idx += 1

        # --- ROL (Badge) ---
        rf = ctk.CTkFrame(row_f, fg_color="transparent", width=self._COL_WIDTHS["Rol"], height=row_h)
        rf.grid(row=0, column=col_idx, padx=4, pady=2, sticky="w")
        rf.pack_propagate(False)
        
        rol_var = "primary" if usuario["rol"] == "Administrador" else "info"
        badge = make_badge(rf, text=usuario["rol"], variant=rol_var)
        badge.pack(side="left")
        col_idx += 1

        # --- ESTADO (Switch) ---
        sf = ctk.CTkFrame(row_f, fg_color="transparent", width=self._COL_WIDTHS["Estado"], height=row_h)
        sf.grid(row=0, column=col_idx, padx=4, pady=2, sticky="w")
        sf.pack_propagate(False)
        
        activo_var = ctk.BooleanVar(value=usuario["activo"])
        ctk.CTkSwitch(
            sf, text="",
            variable=activo_var, width=46,
            progress_color=COLORS["primary"],
            button_color=COLORS["white"],
            command=lambda u=usuario, v=activo_var: self._toggle_estado(u, v),
        ).pack(side="left")
        col_idx += 1

        # --- ACCIONES ---
        af = ctk.CTkFrame(row_f, fg_color="transparent", width=self._COL_WIDTHS["Acciones"], height=row_h)
        af.grid(row=0, column=col_idx, padx=4, pady=2, sticky="w")
        af.pack_propagate(False)
        
        make_button(af, text="✏ Editar", variant="ghost",
                    size="sm",
                    border_color=COLORS["primary"], border_width=1,
                    width=80,
                    command=lambda u=usuario: self._on_editar(u),
                    ).pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Lógica
    # ──────────────────────────────────────────────────────────
    def _filtrar(self, event=None):
        termino = self._search_entry.get().strip().lower()
        filtrados = [
            u for u in self._usuarios
            if termino in u["nombre"].lower()
            or termino in u["dni"].lower()
            or termino in u["email"].lower()
        ] if termino else self._usuarios
        self._render_rows(filtrados)

    def _toggle_estado(self, usuario: dict, var: ctk.BooleanVar):
        """TODO: conectar con backend — actualizar estado en BD"""
        usuario["activo"] = var.get()
        activos = sum(1 for u in self._usuarios if u["activo"])
        self._stats_label.configure(
            text=f"  {len(self._usuarios)} usuarios  ·  {activos} activos"
        )
