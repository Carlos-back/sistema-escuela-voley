"""
Flamingo Sys — Gestión Integral Voley
views/grupos_detalle.py — Detalle de Grupo (HU05 / KAN-33)
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_label, make_card, make_badge, make_divider
from CTkMessagebox import CTkMessagebox


class GruposDetalleView(ctk.CTkFrame):
    """
    Vista de solo lectura con el detalle de un grupo.

    Muestra nombre, horario, descripción, estado y la cantidad de alumnos
    activos vinculados. Las acciones (Editar / Desactivar / Reactivar) solo
    se muestran si el usuario es administrador; el profesor ve solo lectura.

    Parámetros:
        parent        : frame contenedor
        rol           : rol del usuario actual ('administrador' | 'profesor')
        on_volver     : callback() para volver al listado
        on_editar     : callback(grupo) para editar
        on_desactivar : callback(grupo) para baja lógica
        on_reactivar  : callback(grupo) para reactivar
    """

    def __init__(self, parent, rol, on_volver, on_editar, on_desactivar, on_reactivar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._rol = (rol or "").lower()
        self._es_admin = self._rol == "administrador"
        self._on_volver = on_volver
        self._on_editar = on_editar
        self._on_desactivar = on_desactivar
        self._on_reactivar = on_reactivar
        self._grupo = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI (estática; los valores se cargan en cargar())
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Encabezado ────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=2, sticky="ew")

        make_label(header, "🔍  Detalle de Grupo", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Información del grupo y alumnos vinculados.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        make_button(header, text="←  Volver", variant="secondary",
                    command=self._on_volver,
                    ).grid(row=1, column=1, rowspan=2, padx=28, pady=16, sticky="e")

        # ── Body ──────────────────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        # Card principal con los datos
        card = make_card(body)
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        card.grid_columnconfigure(1, weight=1)

        # Título + badge de estado
        self._nombre_label = make_label(card, "—", variant="h3")
        self._nombre_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 6))

        self._estado_container = ctk.CTkFrame(card, fg_color="transparent")
        self._estado_container.grid(row=0, column=1, sticky="e", padx=20, pady=(20, 6))

        make_divider(card).grid(row=1, column=0, columnspan=2,
                                sticky="ew", padx=20, pady=(0, 10))

        # Filas de datos
        self._horario_label = self._add_dato(card, 2, "🕐  Horario")
        self._descripcion_label = self._add_dato(card, 3, "📝  Descripción")
        self._alumnos_label = self._add_dato(card, 4, "👥  Alumnos activos")

        # Espaciado inferior
        ctk.CTkLabel(card, text="", height=6).grid(row=5, column=0)

        # ── Acciones (gated por rol) ──────────────────────────
        self._actions_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._actions_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self._actions_frame.grid_columnconfigure(0, weight=1)

    def _add_dato(self, parent, row, etiqueta):
        cont = ctk.CTkFrame(parent, fg_color="transparent")
        cont.grid(row=row, column=0, columnspan=2, sticky="ew", padx=20, pady=6)
        cont.grid_columnconfigure(1, weight=1)
        make_label(cont, etiqueta, variant="label").grid(row=0, column=0, sticky="w")
        valor = make_label(cont, "—", variant="body")
        valor.grid(row=0, column=1, sticky="w", padx=(16, 0))
        return valor

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def cargar(self, grupo: dict):
        """Carga los datos del grupo y arma las acciones según el rol y estado."""
        self._grupo = grupo or {}
        es_activo = grupo.get("estado", "activo") == "activo"

        self._nombre_label.configure(text=grupo.get("nombre_grupo", "—"))
        self._horario_label.configure(text=grupo.get("horario", "—"))
        self._descripcion_label.configure(text=grupo.get("descripcion") or "—")
        self._alumnos_label.configure(text=str(grupo.get("alumnos_activos", 0)))

        # Badge de estado
        for w in self._estado_container.winfo_children():
            w.destroy()
        make_badge(self._estado_container,
                   text="Activo" if es_activo else "Inactivo",
                   variant="success" if es_activo else "neutral").pack()

        # Acciones
        for w in self._actions_frame.winfo_children():
            w.destroy()

        if not self._es_admin:
            # Profesor: solo lectura
            make_label(self._actions_frame,
                       "👁  Vista de solo lectura", variant="muted"
                       ).grid(row=0, column=0, sticky="w")
            return

        btn_row = ctk.CTkFrame(self._actions_frame, fg_color="transparent")
        btn_row.grid(row=0, column=0, sticky="e")

        make_button(btn_row, text="✏  Editar", variant="primary",
                    command=lambda: self._on_editar(self._grupo)
                    ).pack(side="left", padx=(0, 10))

        if es_activo:
            make_button(btn_row, text="🚫  Desactivar", variant="danger",
                        command=self._confirmar_desactivar).pack(side="left")
        else:
            make_button(btn_row, text="♻  Reactivar", variant="success",
                        command=self._confirmar_reactivar).pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Confirmaciones
    # ──────────────────────────────────────────────────────────
    def _confirmar_desactivar(self):
        msg = CTkMessagebox(
            title="Desactivar grupo",
            message=f"¿Está seguro de desactivar el grupo '{self._grupo.get('nombre_grupo')}'?",
            icon="question", option_1="Cancelar", option_2="Desactivar",
            button_color=COLORS["error"], button_hover_color="#C53030",
        )
        if msg.get() == "Desactivar":
            self._on_desactivar(self._grupo)

    def _confirmar_reactivar(self):
        msg = CTkMessagebox(
            title="Reactivar grupo",
            message=f"¿Reactivar el grupo '{self._grupo.get('nombre_grupo')}'?",
            icon="question", option_1="Cancelar", option_2="Reactivar",
            button_color=COLORS["success"], button_hover_color="#2F855A",
        )
        if msg.get() == "Reactivar":
            self._on_reactivar(self._grupo)
