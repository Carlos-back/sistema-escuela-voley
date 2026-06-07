"""
Flamingo Sys — Gestión Integral Voley
views/alumnos_form.py — Formulario de Alta de Alumno (vinculado a un grupo)
"""

import customtkinter as ctk
import re
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card, make_divider

PLACEHOLDER_GRUPO = "Seleccioná un grupo"


class AlumnosFormView(ctk.CTkFrame):
    """
    Formulario para dar de alta un alumno y vincularlo a un grupo.

    Parámetros:
        parent       : frame contenedor
        on_cancelar  : callback() al presionar Cancelar
        on_registrar : callback(datos_dict) al confirmar

    El combo de grupo se llena con `set_grupos()` (solo grupos activos).
    """

    _REQUERIDOS = ("nombre", "apellido", "dni", "fecha_nacimiento")

    def __init__(self, parent, on_cancelar, on_registrar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_cancelar = on_cancelar
        self._on_registrar = on_registrar
        self._campos = {}
        self._errores = {}
        self._grupos_map = {}   # display -> id_grupo
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, sticky="ew")
        make_label(header, "➕  Nuevo Alumno", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Completá los datos del alumno y asignalo a un grupo.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        card = make_card(body)
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        card.grid_columnconfigure((0, 1), weight=1)

        make_label(card, "Datos del alumno", variant="h3"
                   ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 12))
        make_divider(card).grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 8))

        # Fila: Nombre | Apellido
        self._add_field(card, 2, 0, "nombre",   "👤  Nombre *",   "Ej: Valentina")
        self._add_field(card, 2, 1, "apellido", "👤  Apellido *", "Ej: Ruiz")
        # Fila: DNI | Fecha de nacimiento
        self._add_field(card, 3, 0, "dni", "🪪  DNI *", "12345678")
        self._add_field(card, 3, 1, "fecha_nacimiento", "🎂  Fecha de nacimiento *", "AAAA-MM-DD")
        # Fila: Teléfono | Teléfono tutor
        self._add_field(card, 4, 0, "telefono", "📞  Teléfono", "Opcional")
        self._add_field(card, 4, 1, "telefono_tutor", "📞  Teléfono tutor", "Opcional")
        # Fila: Dirección (full)
        self._add_field(card, 5, 0, "direccion", "🏠  Dirección", "Opcional", col_span=2)

        # Fila: Grupo (combo)
        self._add_grupo_field(card, 6)

        # Error general
        self._error_general = make_label(card, "", variant="error")
        self._error_general.grid(row=7, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 4))

        # Botones
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, sticky="e", padx=20, pady=(8, 24))
        make_button(btn_frame, text="Cancelar", variant="secondary",
                    command=self._on_cancelar).pack(side="left", padx=(0, 10))
        self._submit_btn = make_button(btn_frame, text="  ✔  Registrar Alumno",
                                       variant="primary", command=self._do_submit)
        self._submit_btn.pack(side="left")

        self._refrescar_estado_submit()

    def _add_field(self, parent, row, col, campo_id, label, placeholder, col_span=1):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        px_l = 20 if col == 0 else 8
        px_r = 20 if (col + col_span >= 2) else 8
        container.grid(row=row, column=col, columnspan=col_span,
                       sticky="ew", padx=(px_l, px_r), pady=6)
        container.grid_columnconfigure(0, weight=1)
        make_label(container, label, variant="label").grid(row=0, column=0, sticky="w", pady=(0, 4))
        entry = make_entry(container, placeholder=placeholder)
        entry.grid(row=1, column=0, sticky="ew")
        entry.bind("<KeyRelease>", lambda e, cid=campo_id: self._on_field_change(cid))
        entry.bind("<FocusOut>",   lambda e, cid=campo_id: self._validate_field(cid))
        err = make_label(container, "", variant="error")
        err.grid(row=2, column=0, sticky="w")
        self._campos[campo_id] = entry
        self._errores[campo_id] = err

    def _add_grupo_field(self, parent, row):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=0, columnspan=2, sticky="ew", padx=20, pady=6)
        container.grid_columnconfigure(0, weight=1)
        make_label(container, "🏷  Grupo *", variant="label").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._grupo_var = ctk.StringVar(value=PLACEHOLDER_GRUPO)
        self._grupo_menu = ctk.CTkOptionMenu(
            container, variable=self._grupo_var, values=[PLACEHOLDER_GRUPO],
            font=FONTS.BASE(), height=42, corner_radius=RADIUS.MD,
            fg_color=COLORS["white"], button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"], text_color=COLORS["text_dark"],
            dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"],
            command=lambda _v: self._on_field_change("grupo"),
        )
        self._grupo_menu.grid(row=1, column=0, sticky="ew")
        self._grupo_error = make_label(container, "", variant="error")
        self._grupo_error.grid(row=2, column=0, sticky="w")

    # ──────────────────────────────────────────────────────────
    # Carga de grupos (solo activos)
    # ──────────────────────────────────────────────────────────
    def set_grupos(self, grupos: list):
        """Llena el combo con los grupos activos. grupos: lista de dicts."""
        self._grupos_map = {
            f"{g['nombre_grupo']} — {g['horario']}": g["id_grupo"] for g in grupos
        }
        valores = list(self._grupos_map.keys()) or [PLACEHOLDER_GRUPO]
        self._grupo_menu.configure(values=valores)
        self._grupo_var.set(PLACEHOLDER_GRUPO if self._grupos_map else PLACEHOLDER_GRUPO)

        if not self._grupos_map:
            self._error_general.configure(
                text="⚠  No hay grupos activos. Creá un grupo antes de registrar alumnos.")
        else:
            self._error_general.configure(text="")
        self._refrescar_estado_submit()

    # ──────────────────────────────────────────────────────────
    # Validación
    # ──────────────────────────────────────────────────────────
    def _on_field_change(self, campo_id):
        self._error_general.configure(text="")
        if campo_id in self._REQUERIDOS:
            self._validate_field(campo_id)
        self._refrescar_estado_submit()

    def _validate_field(self, campo_id) -> bool:
        if campo_id == "grupo":
            ok = self._grupo_seleccionado() is not None
            self._grupo_error.configure(text="" if ok else "⚠  Seleccioná un grupo")
            return ok
        if campo_id not in self._campos:
            return True

        entry = self._campos[campo_id]
        err_label = self._errores[campo_id]
        valor = entry.get().strip()
        error = None

        if campo_id in ("nombre", "apellido"):
            etiqueta = "El nombre" if campo_id == "nombre" else "El apellido"
            if not valor:
                error = f"{etiqueta} es obligatorio"
            elif len(valor) < 2:
                error = "Debe tener al menos 2 caracteres"
        elif campo_id == "dni":
            if not valor:
                error = "El DNI es obligatorio"
            elif not (valor.isdigit() and len(valor) in (7, 8)):
                error = "Debe tener 7 u 8 dígitos numéricos"
        elif campo_id == "fecha_nacimiento":
            if not valor:
                error = "La fecha es obligatoria"
            elif not re.match(r"^\d{4}-\d{2}-\d{2}$", valor):
                error = "Formato AAAA-MM-DD"

        if error:
            entry.configure(border_color=COLORS["error"], border_width=2)
            err_label.configure(text=f"⚠  {error}")
            return False
        entry.configure(border_color=COLORS["border"], border_width=2)
        err_label.configure(text="")
        return True

    def _grupo_seleccionado(self):
        return self._grupos_map.get(self._grupo_var.get())

    def _hay_requeridos_completos(self) -> bool:
        return (all(self._campos[c].get().strip() for c in self._REQUERIDOS)
                and self._grupo_seleccionado() is not None)

    def _refrescar_estado_submit(self):
        if self._hay_requeridos_completos():
            self._submit_btn.configure(state="normal", fg_color=COLORS["primary"],
                                       hover_color=COLORS["primary_hover"])
        else:
            self._submit_btn.configure(state="disabled", fg_color="#CCCCCC", hover_color="#AAAAAA")

    # ──────────────────────────────────────────────────────────
    # Submit / API pública
    # ──────────────────────────────────────────────────────────
    def _do_submit(self):
        validos = [self._validate_field(c) for c in self._REQUERIDOS]
        validos.append(self._validate_field("grupo"))
        if not all(validos):
            return
        datos = {
            "nombre":          self._campos["nombre"].get().strip(),
            "apellido":        self._campos["apellido"].get().strip(),
            "dni":             self._campos["dni"].get().strip(),
            "fecha_nacimiento": self._campos["fecha_nacimiento"].get().strip(),
            "telefono":        self._campos["telefono"].get().strip(),
            "telefono_tutor":  self._campos["telefono_tutor"].get().strip(),
            "direccion":       self._campos["direccion"].get().strip(),
            "id_grupo":        self._grupo_seleccionado(),
        }
        self._on_registrar(datos)

    def mostrar_error(self, mensaje: str):
        self._error_general.configure(text=f"⚠  {mensaje}")

    def limpiar(self):
        self._error_general.configure(text="")
        for campo_id, entry in self._campos.items():
            entry.delete(0, "end")
            entry.configure(border_color=COLORS["border"], border_width=2)
            self._errores[campo_id].configure(text="")
        self._grupo_var.set(PLACEHOLDER_GRUPO)
        self._grupo_error.configure(text="")
        self._refrescar_estado_submit()
