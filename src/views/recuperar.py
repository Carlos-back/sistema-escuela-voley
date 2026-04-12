"""
Flamingo Sys — Gestión Integral Voley
views/recuperar.py — Pantalla de recuperación de contraseña
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card


class RecuperarView(ctk.CTkFrame):
    """
    Vista de recuperación de contraseña.

    Parámetros:
        parent  : ventana raíz
        on_back : callback() para volver al login
    """

    # TODO: conectar con backend — emails registrados en BD
    _MOCK_EMAILS = ["reciolauti@gmail.com", "carlos@flamingo.com"]

    def __init__(self, parent, on_back):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_back = on_back
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

        ctk.CTkLabel(inner, text="🦩", font=FONTS.XXXL()).pack(pady=(0, 12))
        make_label(inner, "Flamingo Sys", variant="h1",
                   text_color=COLORS["primary"]).pack()
        make_label(inner, "Gestión Integral · Voley",
                   text_color=COLORS["sidebar_text"]).pack(pady=(4, 0))

        ctk.CTkFrame(inner, height=3, width=100,
                     fg_color=COLORS["primary"], corner_radius=2).pack(pady=(20, 0))

        make_label(inner,
                   "Te enviamos un link a tu email\npara recuperar tu acceso.",
                   variant="muted", justify="center").pack(pady=(14, 0))

        # ── Panel derecho (formulario) ─────────────────────────
        right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        card = make_card(right)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="🔑", font=FONTS.XXXL()).grid(
            row=0, column=0, pady=(36, 8))

        make_label(card, "Recuperar Contraseña", variant="h2"
                   ).grid(row=1, column=0, padx=36)

        make_label(card,
                   "Ingresá el email asociado a tu cuenta\n"
                   "y te enviaremos un enlace de recuperación.",
                   variant="muted", justify="center"
                   ).grid(row=2, column=0, padx=36, pady=(6, 24))

        # ── Campo email ───────────────────────────────────────
        make_label(card, "✉  Email", variant="label"
                   ).grid(row=3, column=0, sticky="w", padx=36, pady=(0, 4))

        self._email_entry = make_entry(card, placeholder="tu@email.com")
        self._email_entry.grid(row=4, column=0, sticky="ew", padx=36, pady=(0, 4))
        self._email_entry.bind("<Return>",   lambda e: self._do_enviar())
        self._email_entry.bind("<FocusIn>",  lambda e: self._reset_feedback())

        self._email_error = make_label(card, "", variant="error")
        self._email_error.grid(row=5, column=0, sticky="w", padx=36, pady=(0, 8))

        self._feedback_label = make_label(card, "", variant="success",
                                          wraplength=320, justify="center")
        self._feedback_label.grid(row=6, column=0, padx=36, pady=(0, 8))

        # ── Botón Enviar ──────────────────────────────────────
        self._send_btn = make_button(
            card, text="  Enviar enlace de recuperación",
            variant="primary", size="lg",
            command=self._do_enviar,
        )
        self._send_btn.grid(row=7, column=0, sticky="ew", padx=36, pady=(4, 12))

        make_button(card, text="← Volver al inicio de sesión", variant="ghost",
                    font=ctk.CTkFont(size=12, underline=True),
                    command=self._on_back,
                    ).grid(row=8, column=0, pady=(0, 30))

    # ──────────────────────────────────────────────────────────
    # Lógica
    # ──────────────────────────────────────────────────────────
    def _do_enviar(self):
        """
        TODO: conectar con backend — verificar email en BD y enviar link real
        """
        email = self._email_entry.get().strip()
        self._reset_feedback()

        if not email:
            self._set_error("El email es obligatorio")
            return
        if "@" not in email or "." not in email:
            self._set_error("Ingresá un email válido")
            return

        # TODO: conectar con backend — validar email contra BD
        if email in self._MOCK_EMAILS:
            self._feedback_label.configure(
                text=f"✅  ¡Listo! Te enviamos un enlace de recuperación a\n{email}",
                text_color=COLORS["success"],
            )
            self._send_btn.configure(state="disabled", text="✔  Email enviado")
            self._email_entry.configure(state="disabled")
        else:
            self._set_error("No encontramos una cuenta con ese email")

    def _set_error(self, msg: str):
        self._email_entry.configure(border_color=COLORS["error"], border_width=2)
        self._email_error.configure(text=f"⚠  {msg}")
        self._feedback_label.configure(text="")

    def _reset_feedback(self):
        self._email_entry.configure(border_color=COLORS["border"], border_width=2)
        self._email_error.configure(text="")
        self._feedback_label.configure(text="")
        self._send_btn.configure(state="normal",
                                 text="  Enviar enlace de recuperación")
