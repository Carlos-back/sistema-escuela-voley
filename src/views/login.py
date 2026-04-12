"""
Flamingo Sys — Gestión Integral Voley
views/login.py — Pantalla de inicio de sesión
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card, make_accent_bar
from services.auth import login as api_login


class LoginView(ctk.CTkFrame):
    """
    Vista de login — panel oscuro decorativo + card de formulario.

    Parámetros:
        parent      : ventana raíz
        on_login    : callback(user_dict) al login exitoso
        on_recuperar: callback() para ir a recuperar contraseña
    """

    def __init__(self, parent, on_login, on_recuperar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_login = on_login
        self._on_recuperar = on_recuperar
        self._show_password = False
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Panel izquierdo decorativo ─────────────────────────
        left = ctk.CTkFrame(self, fg_color=COLORS["sidebar_bg"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.grid(row=0, column=0)

        ctk.CTkLabel(inner, text="🦩", font=FONTS.XXXL()).pack(pady=(0, 16))

        make_label(inner, "Flamingo Sys", variant="h1",
                   text_color=COLORS["primary"]).pack()
        make_label(inner, "Gestión Integral · Voley",
                   text_color=COLORS["sidebar_text"]).pack(pady=(4, 0))

        ctk.CTkFrame(inner, height=3, width=120,
                     fg_color=COLORS["primary"], corner_radius=2).pack(pady=(24, 0))

        make_label(inner,
                   "Sistema municipal de gestión\npara escuelas de vóley",
                   variant="muted", justify="center").pack(pady=(16, 0))

        # ── Panel derecho (formulario) ─────────────────────────
        right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        card = make_card(right)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)
        card.grid_columnconfigure(0, weight=1)

        # Título
        make_label(card, "Iniciar Sesión", variant="h2"
                   ).grid(row=0, column=0, sticky="w", padx=36, pady=(36, 4))
        make_label(card, "Ingresá tus credenciales para continuar",
                   variant="muted"
                   ).grid(row=1, column=0, sticky="w", padx=36, pady=(0, 24))

        # ── Campo DNI ─────────────────────────────────────────
        make_label(card, "🪪  DNI", variant="label"
                   ).grid(row=2, column=0, sticky="w", padx=36, pady=(0, 4))

        self._dni_entry = make_entry(card, placeholder="Ingresá tu DNI")
        self._dni_entry.grid(row=3, column=0, sticky="ew", padx=36, pady=(0, 4))
        self._dni_entry.bind("<FocusIn>", lambda e: self._clear_error(self._dni_entry))
        self._dni_entry.bind("<Return>",  lambda e: self._do_login())

        self._dni_error = make_label(card, "", variant="error")
        self._dni_error.grid(row=4, column=0, sticky="w", padx=36, pady=(0, 8))

        # ── Campo Contraseña ──────────────────────────────────
        make_label(card, "🔒  Contraseña", variant="label"
                   ).grid(row=5, column=0, sticky="w", padx=36, pady=(0, 4))

        pw_frame = ctk.CTkFrame(card, fg_color="transparent")
        pw_frame.grid(row=6, column=0, sticky="ew", padx=36, pady=(0, 4))
        pw_frame.grid_columnconfigure(0, weight=1)

        self._pw_entry = make_entry(pw_frame, placeholder="Ingresá tu contraseña",
                                   show="●")
        self._pw_entry.grid(row=0, column=0, sticky="ew")
        self._pw_entry.bind("<FocusIn>", lambda e: self._clear_error(self._pw_entry))
        self._pw_entry.bind("<Return>",  lambda e: self._do_login())

        self._toggle_btn = ctk.CTkButton(
            pw_frame, text="👁", width=44, height=42,
            corner_radius=RADIUS.MD,
            fg_color=COLORS["border"], hover_color="#D1D5DB",
            text_color=COLORS["text_dark"],
            command=self._toggle_password,
        )
        self._toggle_btn.grid(row=0, column=1, padx=(8, 0))

        self._pw_error = make_label(card, "", variant="error")
        self._pw_error.grid(row=7, column=0, sticky="w", padx=36, pady=(0, 4))

        # Error general
        self._general_error = make_label(card, "", variant="error")
        self._general_error.grid(row=8, column=0, pady=(0, 4))

        # Botón ingresar
        make_button(card, text="Ingresar", variant="primary", size="lg",
                    command=self._do_login
                    ).grid(row=9, column=0, sticky="ew", padx=36, pady=(8, 12))

        # Link recuperar
        make_button(card, text="¿Olvidaste tu contraseña?", variant="ghost",
                    font=ctk.CTkFont(size=12, underline=True),
                    command=self._on_recuperar,
                    ).grid(row=10, column=0, pady=(0, 30))

    # ──────────────────────────────────────────────────────────
    # Lógica
    # ──────────────────────────────────────────────────────────
    def _do_login(self):
        """
        TODO: conectar con backend — llamar a API de autenticación
        """
        dni = self._dni_entry.get().strip()
        pwd = self._pw_entry.get().strip()
        self._general_error.configure(text="")
        errors = False

        if not dni:
            self._set_error(self._dni_entry, self._dni_error, "El DNI es obligatorio")
            errors = True
        else:
            self._clear_error(self._dni_entry)

        if not pwd:
            self._set_error(self._pw_entry, self._pw_error, "La contraseña es obligatoria")
            errors = True
        else:
            self._clear_error(self._pw_entry)

        if errors:
            return

        # TODO: conectar con backend — reemplazar mock con llamada real
        user = self._authenticate(dni, pwd)
        if user:
            self._on_login(user)
        else:
            self._general_error.configure(text="❌  DNI o contraseña incorrectos")

    def _authenticate(self, dni: str, pwd: str):
        """Valida credenciales contra la BD SQLite."""
        return api_login(dni, pwd)

    def _toggle_password(self):
        self._show_password = not self._show_password
        self._pw_entry.configure(show="" if self._show_password else "●")
        self._toggle_btn.configure(text="🙈" if self._show_password else "👁")

    def _set_error(self, entry: ctk.CTkEntry, label: ctk.CTkLabel, msg: str):
        entry.configure(border_color=COLORS["error"], border_width=2)
        label.configure(text=f"⚠  {msg}")

    def _clear_error(self, entry: ctk.CTkEntry):
        entry.configure(border_color=COLORS["border"], border_width=2)
        if entry == self._dni_entry:
            self._dni_error.configure(text="")
        elif entry == self._pw_entry:
            self._pw_error.configure(text="")
        self._general_error.configure(text="")
