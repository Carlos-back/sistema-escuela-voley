"""
Flamingo Sys — Gestión Integral Voley
views/perfil.py — Edición de perfil del usuario actual
"""

import customtkinter as ctk
import re
import tkinter.messagebox as tkmb
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card, make_divider, make_badge

try:
    from CTkMessagebox import CTkMessagebox
    CTKMSGBOX_OK = True
except ImportError:
    CTKMSGBOX_OK = False


class PerfilView(ctk.CTkFrame):
    """
    Vista de edición del perfil del usuario logueado.

    Parámetros:
        parent     : frame contenedor
        user       : dict con datos del usuario actual
        on_guardado: callback(datos_dict) tras guardar cambios
    """

    def __init__(self, parent, user: dict, on_guardado):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._user = dict(user or {})
        self._on_guardado = on_guardado
        self._originales = {}
        self._campos = {}
        self._errores = {}
        self._show_pw = False

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
                     corner_radius=0).grid(row=0, column=0, sticky="ew")

        make_label(header, "👤  Mi Perfil", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Editá tus datos personales. Tu DNI no puede modificarse.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        # ── Body scrollable ───────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        # ── Card avatar ───────────────────────────────────────
        nombre    = self._user.get("nombre", "Usuario")
        rol       = self._user.get("rol", "").capitalize()
        email_val = self._user.get("email", "")

        avatar_card = make_card(body)
        avatar_card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        avatar_card.grid_columnconfigure(1, weight=1)

        avatar_outer = ctk.CTkFrame(avatar_card, width=72, height=72,
                                    corner_radius=36, fg_color=COLORS["primary"])
        avatar_outer.grid(row=0, column=0, rowspan=3, padx=(24, 16), pady=20)
        avatar_outer.grid_propagate(False)
        ctk.CTkLabel(avatar_outer,
                     text=nombre[0].upper() if nombre else "U",
                     font=FONTS.XXXL_BOLD(), text_color="white"
                     ).place(relx=0.5, rely=0.5, anchor="center")

        make_label(avatar_card, nombre, variant="h3"
                   ).grid(row=0, column=1, sticky="w", pady=(20, 2))
        make_badge(avatar_card, text=rol, variant="primary"
                   ).grid(row=1, column=1, sticky="w")
        make_label(avatar_card, email_val, variant="muted"
                   ).grid(row=2, column=1, sticky="w", pady=(2, 20))

        # ── Card formulario ───────────────────────────────────
        form_card = make_card(body)
        form_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        form_card.grid_columnconfigure((0, 1), weight=1)

        make_label(form_card, "Datos personales", variant="h3"
                   ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 12))
        make_divider(form_card).grid(row=1, column=0, columnspan=2,
                                     sticky="ew", padx=20, pady=(0, 12))

        self._add_field(form_card, 2, 0, "dni",    "🪪  DNI",  disabled=True)
        self._add_field(form_card, 2, 1, "rol",    "🎭  Rol",  disabled=True)
        self._add_field(form_card, 3, 0, "nombre", "👤  Nombre *")
        self._add_field(form_card, 3, 1, "email",  "✉  Email *")

        # ── Card contraseña ───────────────────────────────────
        pw_card = make_card(body)
        pw_card.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        pw_card.grid_columnconfigure(0, weight=1)

        make_label(pw_card, "Cambio de contraseña", variant="h3"
                   ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))
        make_label(pw_card, "Dejá en blanco si no querés cambiar tu contraseña.",
                   variant="muted"
                   ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))
        make_divider(pw_card).grid(row=2, column=0, sticky="ew",
                                   padx=20, pady=(0, 8))

        self._add_password_field(pw_card, 3)

        # ── Botón Guardar ─────────────────────────────────────
        btn_frame = ctk.CTkFrame(body, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="e", padx=20, pady=(8, 24))

        self._save_btn = ctk.CTkButton(
            btn_frame, text="💾  Guardar Cambios",
            font=FONTS.BASE_BOLD(),
            fg_color="#CCCCCC", hover_color="#AAAAAA",
            text_color="white", height=42, width=180,
            corner_radius=RADIUS.MD, state="disabled",
            command=self._do_guardar,
        )
        self._save_btn.pack()

        self._precargar_datos()

    # ──────────────────────────────────────────────────────────
    # Helpers de campos
    # ──────────────────────────────────────────────────────────
    def _add_field(self, parent, row: int, col: int,
                   campo_id: str, label: str, disabled: bool = False):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        px_l = 20 if col == 0 else 8
        px_r = 8  if col == 0 else 20
        container.grid(row=row, column=col, sticky="ew",
                       padx=(px_l, px_r), pady=6)
        container.grid_columnconfigure(0, weight=1)

        make_label(container, label, variant="label").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        entry = make_entry(
            container,
            state="disabled" if disabled else "normal",
            fg_color="#F3F4F6" if disabled else COLORS["white"],
            text_color=COLORS["text_muted"] if disabled else COLORS["text_dark"],
        )
        entry.grid(row=1, column=0, sticky="ew")

        if not disabled:
            entry.bind("<KeyRelease>", lambda e: self._on_change())

        err = make_label(container, "", variant="error")
        err.grid(row=2, column=0, sticky="w")

        self._campos[campo_id]  = entry
        self._errores[campo_id] = err

    def _add_password_field(self, parent, row: int):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 20))
        container.grid_columnconfigure(0, weight=1)

        make_label(container, "🔒  Nueva contraseña", variant="label").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        pw_row = ctk.CTkFrame(container, fg_color="transparent")
        pw_row.grid(row=1, column=0, sticky="ew")
        pw_row.grid_columnconfigure(0, weight=1)

        self._pw_entry = make_entry(pw_row, placeholder="Nueva contraseña (opcional)",
                                    show="●")
        self._pw_entry.grid(row=0, column=0, sticky="ew")
        self._pw_entry.bind("<KeyRelease>", lambda e: self._on_change())

        ctk.CTkButton(
            pw_row, text="👁", width=42, height=42,
            corner_radius=RADIUS.MD,
            fg_color=COLORS["border"], hover_color="#D1D5DB",
            text_color=COLORS["text_dark"],
            command=self._toggle_pw,
        ).grid(row=0, column=1, padx=(8, 0))

        self._pw_error = make_label(container, "", variant="error")
        self._pw_error.grid(row=2, column=0, sticky="w")

    # ──────────────────────────────────────────────────────────
    # Precarga y detección de cambios
    # ──────────────────────────────────────────────────────────
    def _precargar_datos(self):
        """TODO: conectar con backend — datos frescos desde BD"""
        datos = {
            "dni":    self._user.get("dni", ""),
            "rol":    self._user.get("rol", "").capitalize(),
            "nombre": self._user.get("nombre", ""),
            "email":  self._user.get("email", ""),
        }
        for campo_id, valor in datos.items():
            entry = self._campos.get(campo_id)
            if entry:
                if entry.cget("state") == "disabled":
                    entry.configure(state="normal")
                    entry.delete(0, "end")
                    entry.insert(0, valor)
                    entry.configure(state="disabled")
                else:
                    entry.delete(0, "end")
                    entry.insert(0, valor)
        self._originales = datos.copy()

    def _on_change(self):
        """Habilita el botón solo si hay cambios."""
        hay_cambios = any(
            self._campos[cid].get().strip() != orig
            for cid, orig in self._originales.items()
            if cid in self._campos and self._campos[cid].cget("state") != "disabled"
        ) or bool(self._pw_entry.get().strip())

        if hay_cambios:
            self._save_btn.configure(state="normal",
                                     fg_color=COLORS["primary"],
                                     hover_color=COLORS["primary_hover"])
        else:
            self._save_btn.configure(state="disabled",
                                     fg_color="#CCCCCC", hover_color="#AAAAAA")

    # ──────────────────────────────────────────────────────────
    # Validación y guardado
    # ──────────────────────────────────────────────────────────
    def _validate(self) -> bool:
        ok = True
        nombre = self._campos["nombre"].get().strip()
        email  = self._campos["email"].get().strip()
        pw     = self._pw_entry.get().strip()

        if not nombre or len(nombre) < 2:
            self._campos["nombre"].configure(border_color=COLORS["error"])
            self._errores["nombre"].configure(text="⚠  El nombre es obligatorio")
            ok = False
        else:
            self._campos["nombre"].configure(border_color=COLORS["border"])
            self._errores["nombre"].configure(text="")

        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            self._campos["email"].configure(border_color=COLORS["error"])
            self._errores["email"].configure(text="⚠  Email inválido")
            ok = False
        else:
            self._campos["email"].configure(border_color=COLORS["border"])
            self._errores["email"].configure(text="")

        if pw and len(pw) < 6:
            self._pw_entry.configure(border_color=COLORS["error"])
            self._pw_error.configure(text="⚠  Mínimo 6 caracteres")
            ok = False
        else:
            self._pw_entry.configure(border_color=COLORS["border"])
            self._pw_error.configure(text="")

        return ok

    def _do_guardar(self):
        """TODO: conectar con backend — actualizar usuario en BD"""
        if not self._validate():
            return
        if not self._confirmar():
            return

        datos = {
            "nombre":   self._campos["nombre"].get().strip(),
            "email":    self._campos["email"].get().strip(),
            "password": self._pw_entry.get().strip() or None,
        }
        self._user.update(datos)
        self._originales["nombre"] = datos["nombre"]
        self._originales["email"]  = datos["email"]
        self._pw_entry.delete(0, "end")
        self._save_btn.configure(state="disabled",
                                 fg_color="#CCCCCC", hover_color="#AAAAAA")
        self._mostrar_exito()
        self._on_guardado(datos)

    def _confirmar(self) -> bool:
        if CTKMSGBOX_OK:
            msg = CTkMessagebox(
                title="Confirmar cambios",
                message="¿Estás seguro de que querés guardar los cambios en tu perfil?",
                icon="question",
                option_1="Cancelar", option_2="Guardar",
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary_hover"],
            )
            return msg.get() == "Guardar"
        return tkmb.askyesno("Confirmar cambios",
                             "¿Guardás los cambios en tu perfil?")

    def _mostrar_exito(self):
        toast = ctk.CTkFrame(self, fg_color=COLORS["success_light"],
                             corner_radius=10,
                             border_width=1, border_color="#6EE7B7")
        toast.place(relx=0.5, rely=0.92, anchor="center", relwidth=0.5)
        make_label(toast, "✅  Perfil actualizado correctamente",
                   variant="success", font=FONTS.BASE_BOLD()).pack(pady=12, padx=20)
        self.after(3000, toast.destroy)

    def _toggle_pw(self):
        self._show_pw = not self._show_pw
        self._pw_entry.configure(show="" if self._show_pw else "●")
