"""
Flamingo Sys — Gestión Integral Voley
views/usuarios_form.py — Formulario nuevo/edición de usuario
"""

import customtkinter as ctk
import re
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card, make_divider


class UsuariosFormView(ctk.CTkFrame):
    """
    Formulario para crear o editar un usuario.

    Parámetros:
        parent      : frame contenedor
        on_cancelar : callback() al presionar Cancelar
        on_registrar: callback(datos_dict) al confirmar
    """

    def __init__(self, parent, on_cancelar, on_registrar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_cancelar = on_cancelar
        self._on_registrar = on_registrar
        self._modo_edicion = False
        self._current_id = None
        self._show_password = False
        self._campos = {}
        self._errores = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Encabezado ────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=2, sticky="ew")

        self._titulo_label = make_label(header, "➕  Nuevo Usuario", variant="h2")
        self._titulo_label.grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))

        self._subtitulo_label = make_label(
            header,
            "Completá los datos para registrar un nuevo usuario en el sistema.",
            variant="muted",
        )
        self._subtitulo_label.grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        # ── Cuerpo scrollable ─────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure((0, 1), weight=1)

        card = make_card(body)
        card.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
        card.grid_columnconfigure((0, 1), weight=1)

        # Fila 1: DNI + Rol
        self._add_field(card, 0, 0, "dni",  "🪪  DNI *",  "12345678")
        self._add_rol_field(card, 0, 1)

        make_divider(card).grid(row=1, column=0, columnspan=2,
                                sticky="ew", padx=20, pady=(4, 8))

        # Fila 2: Nombre + Apellido
        self._add_field(card, 2, 0, "nombre",   "👤  Nombre *",   "Ej: Laura")
        self._add_field(card, 2, 1, "apellido",  "👤  Apellido *",  "Ej: García")

        # Fila 3: Email
        self._add_field(card, 3, 0, "email", "✉  Email *",
                        "usuario@flamingo.com", col_span=2)

        # Fila 4: Contraseña
        self._add_password_field(card, 4)

        # ── Botones ───────────────────────────────────────────
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=2, sticky="e",
                       padx=20, pady=(8, 24))

        make_button(btn_frame, text="Cancelar", variant="secondary",
                    command=self._on_cancelar,
                    ).pack(side="left", padx=(0, 10))

        self._submit_btn = make_button(btn_frame,
                                       text="  ✔  Registrar Usuario",
                                       variant="primary",
                                       command=self._do_submit)
        self._submit_btn.pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Helpers de campos
    # ──────────────────────────────────────────────────────────
    def _add_field(self, parent, row: int, col: int, campo_id: str,
                   label: str, placeholder: str,
                   col_span: int = 1, disabled: bool = False):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        px_l = 20 if col == 0 else 8
        px_r = 20 if (col + col_span >= 2) else 8
        container.grid(row=row, column=col, columnspan=col_span,
                       sticky="ew", padx=(px_l, px_r), pady=6)
        container.grid_columnconfigure(0, weight=1)

        make_label(container, label, variant="label").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        entry = make_entry(container, placeholder=placeholder,
                           state="disabled" if disabled else "normal",
                           fg_color="#F3F4F6" if disabled else COLORS["white"],
                           text_color=COLORS["text_muted"] if disabled else COLORS["text_dark"])
        entry.grid(row=1, column=0, sticky="ew")
        entry.bind("<KeyRelease>", lambda e, cid=campo_id: self._validate_field(cid))
        entry.bind("<FocusOut>",   lambda e, cid=campo_id: self._validate_field(cid))

        err = make_label(container, "", variant="error")
        err.grid(row=2, column=0, sticky="w")

        self._campos[campo_id]  = entry
        self._errores[campo_id] = err

    def _add_rol_field(self, parent, row: int, col: int):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=col, sticky="ew", padx=(8, 20), pady=6)
        container.grid_columnconfigure(0, weight=1)

        make_label(container, "🎭  Rol *", variant="label").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        self._rol_var = ctk.StringVar(value="Administrador")
        ctk.CTkOptionMenu(
            container,
            variable=self._rol_var,
            values=["Administrador", "Profesor"],
            font=FONTS.BASE(), height=42, corner_radius=RADIUS.MD,
            fg_color=COLORS["white"],
            button_color=COLORS["primary"], button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text_dark"],
            dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"],
        ).grid(row=1, column=0, sticky="ew")
        self._campos["rol"] = None   # no usa CTkEntry

    def _add_password_field(self, parent, row: int):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=0, columnspan=2,
                       sticky="ew", padx=20, pady=6)
        container.grid_columnconfigure(0, weight=1)

        make_label(container, "🔒  Contraseña *", variant="label").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        pw_row = ctk.CTkFrame(container, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew")
        pw_row.grid_columnconfigure(0, weight=1)

        self._pw_entry = make_entry(pw_row, placeholder="Mínimo 6 caracteres", show="●")
        self._pw_entry.grid(row=0, column=0, sticky="ew")
        self._pw_entry.bind("<KeyRelease>", lambda e: self._validate_field("password"))

        self._pw_toggle = ctk.CTkButton(
            pw_row, text="👁", width=42, height=42,
            corner_radius=RADIUS.MD,
            fg_color=COLORS["border"], hover_color="#D1D5DB",
            text_color=COLORS["text_dark"],
            command=self._toggle_password,
        )
        self._pw_toggle.grid(row=0, column=1, padx=(8, 0))

        self._campos["password"]  = self._pw_entry
        self._errores["password"] = make_label(container, "", variant="error")
        self._errores["password"].grid(row=2, column=0, sticky="w")

        # Indicador de fortaleza
        strength_row = ctk.CTkFrame(container, fg_color="transparent")
        strength_row.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._strength_bars = []
        for _ in range(4):
            bar = ctk.CTkFrame(strength_row, height=4,
                               fg_color=COLORS["border"], corner_radius=2)
            bar.pack(side="left", fill="x", expand=True, padx=(0, 3))
            self._strength_bars.append(bar)
        self._strength_label = make_label(strength_row, "", variant="caption")
        self._strength_label.pack(side="left", padx=(8, 0))

    # ──────────────────────────────────────────────────────────
    # Validaciones
    # ──────────────────────────────────────────────────────────
    def _validate_field(self, campo_id: str) -> bool:
        entry = self._campos.get(campo_id)
        err_label = self._errores.get(campo_id)
        if entry is None or err_label is None:
            return True

        valor = entry.get().strip() if hasattr(entry, "get") else ""
        error = None

        if campo_id == "dni":
            if not valor:                                   error = "El DNI es obligatorio"
            elif not valor.isdigit():                       error = "Solo puede contener números"
            elif len(valor) not in (7, 8):                 error = "Debe tener 7 u 8 dígitos"
        elif campo_id in ("nombre", "apellido"):
            if not valor:  error = f"{'El nombre' if campo_id == 'nombre' else 'El apellido'} es obligatorio"
            elif len(valor) < 2: error = "Debe tener al menos 2 caracteres"
        elif campo_id == "email":
            if not valor:  error = "El email es obligatorio"
            elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", valor): error = "Ingresá un email válido"
        elif campo_id == "password":
            if not self._modo_edicion:
                if not valor:          error = "La contraseña es obligatoria"
                elif len(valor) < 6:   error = "Debe tener al menos 6 caracteres"
            self._update_strength(valor)

        if error:
            entry.configure(border_color=COLORS["error"], border_width=2)
            err_label.configure(text=f"⚠  {error}", text_color=COLORS["error"])
            return False
        else:
            entry.configure(border_color=COLORS["border"], border_width=2)
            err_label.configure(text="✓" if valor else "", text_color=COLORS["success"])
            return True

    def _validate_all(self) -> bool:
        campos = ["dni", "nombre", "apellido", "email"]
        if not self._modo_edicion:
            campos.append("password")
        return all(self._validate_field(c) for c in campos)

    def _update_strength(self, pwd: str):
        fuerza = sum([
            len(pwd) >= 6,
            bool(re.search(r"[A-Z]", pwd)),
            bool(re.search(r"\d", pwd)),
            bool(re.search(r"[^A-Za-z0-9]", pwd)),
        ])
        colores = {0: COLORS["border"], 1: "#F87171", 2: "#FBBF24",
                   3: "#34D399", 4: COLORS["success"]}
        textos  = {0: "", 1: "Débil", 2: "Regular", 3: "Buena", 4: "Fuerte"}
        col = colores[fuerza]
        for i, bar in enumerate(self._strength_bars):
            bar.configure(fg_color=col if i < fuerza else COLORS["border"])
        self._strength_label.configure(text=textos[fuerza], text_color=col)

    def _toggle_password(self):
        self._show_password = not self._show_password
        self._pw_entry.configure(show="" if self._show_password else "●")
        self._pw_toggle.configure(text="🙈" if self._show_password else "👁")

    # ──────────────────────────────────────────────────────────
    # Submit
    # ──────────────────────────────────────────────────────────
    def _do_submit(self):
        """TODO: conectar con backend — insertar o actualizar usuario en BD"""
        if not self._validate_all():
            return
        datos = {
            "id_usuario": self._current_id,
            "dni":      self._campos["dni"].get().strip(),
            "nombre":   self._campos["nombre"].get().strip(),
            "apellido": self._campos["apellido"].get().strip(),
            "email":    self._campos["email"].get().strip(),
            "rol":      self._rol_var.get(),
            "password": self._pw_entry.get().strip() or None,
        }
        self._on_registrar(datos)

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def cargar_usuario(self, usuario: dict):
        """Precarga el formulario para edición."""
        self._modo_edicion = True
        self._current_id = usuario.get("id_usuario")
        self._titulo_label.configure(text="✏  Editar Usuario")
        self._subtitulo_label.configure(
            text="Modificá los datos del usuario. El DNI no puede cambiarse.")
        self._submit_btn.configure(text="  ✔  Guardar Cambios")

        for campo_id, key in [("dni", "dni"), ("nombre", "nombre"),
                               ("apellido", "apellido"), ("email", "email")]:
            e = self._campos.get(campo_id)
            if e:
                e.delete(0, "end")
                e.insert(0, usuario.get(key, ""))

        self._campos["dni"].configure(state="disabled", fg_color="#F3F4F6")
        self._rol_var.set(usuario.get("rol", "Administrador"))
        self._pw_entry.delete(0, "end")

    def limpiar(self):
        """Resetea el formulario al estado de nuevo usuario."""
        self._modo_edicion = False
        self._current_id = None
        self._titulo_label.configure(text="➕  Nuevo Usuario")
        self._subtitulo_label.configure(
            text="Completá los datos para registrar un nuevo usuario en el sistema.")
        self._submit_btn.configure(text="  ✔  Registrar Usuario")

        for campo_id, entry in self._campos.items():
            if hasattr(entry, "delete"):
                entry.configure(state="normal", fg_color=COLORS["white"])
                entry.delete(0, "end")
            if campo_id in self._errores and self._errores[campo_id]:
                self._errores[campo_id].configure(text="")
            if hasattr(entry, "configure"):
                entry.configure(border_color=COLORS["border"])

        self._rol_var.set("Administrador")
        self._pw_entry.delete(0, "end")
        for bar in self._strength_bars:
            bar.configure(fg_color=COLORS["border"])
        self._strength_label.configure(text="")
