"""
Flamingo Sys — Gestión Integral Voley
views/alumnos_detalle.py — Detalle de Alumno (HU02 / HU03)
"""

from datetime import date, datetime

import customtkinter as ctk
from theme import COLORS, make_button, make_label, make_card, make_badge, make_divider
from CTkMessagebox import CTkMessagebox


class AlumnosDetalleView(ctk.CTkFrame):
    """
    Vista de solo lectura con el detalle de un alumno.

    Muestra los datos personales, el grupo asignado y la fecha de
    inscripción. Las acciones (Editar / Desactivar / Reactivar) solo se
    muestran si el usuario es administrador; el profesor ve solo lectura.

    Parámetros:
        parent        : frame contenedor
        rol           : rol del usuario actual ('administrador' | 'profesor')
        on_volver     : callback() para volver al listado
        on_editar     : callback(alumno) para editar
        on_desactivar : callback(alumno) para baja lógica
        on_reactivar  : callback(alumno) para reactivar
    """

    def __init__(self, parent, rol, on_volver, on_editar, on_desactivar, on_reactivar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._rol = (rol or "").lower()
        self._es_admin = self._rol == "administrador"
        self._on_volver = on_volver
        self._on_editar = on_editar
        self._on_desactivar = on_desactivar
        self._on_reactivar = on_reactivar
        self._alumno = {}

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

        make_label(header, "🔍  Detalle de Alumno", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Datos personales, grupo e inscripción del alumno.",
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

        # Card de datos personales
        card = make_card(body)
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        card.grid_columnconfigure(1, weight=1)

        # Nombre + badge de estado
        self._nombre_label = make_label(card, "—", variant="h3")
        self._nombre_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 6))

        self._estado_container = ctk.CTkFrame(card, fg_color="transparent")
        self._estado_container.grid(row=0, column=1, sticky="e", padx=20, pady=(20, 6))

        make_divider(card).grid(row=1, column=0, columnspan=2,
                                sticky="ew", padx=20, pady=(0, 10))

        self._dni_label = self._add_dato(card, 2, "🪪  DNI")
        self._nacimiento_label = self._add_dato(card, 3, "🎂  Fecha de nacimiento")
        self._telefono_label = self._add_dato(card, 4, "📞  Teléfono")
        self._tutor_label = self._add_dato(card, 5, "📞  Teléfono tutor")
        self._direccion_label = self._add_dato(card, 6, "🏠  Dirección")
        ctk.CTkLabel(card, text="", height=6).grid(row=7, column=0)

        # Card de inscripción
        insc_card = make_card(body)
        insc_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        insc_card.grid_columnconfigure(1, weight=1)
        make_label(insc_card, "🏐  Inscripción", variant="h3"
                   ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 8))
        make_divider(insc_card).grid(row=1, column=0, columnspan=2,
                                     sticky="ew", padx=20, pady=(0, 10))
        self._grupo_label = self._add_dato(insc_card, 2, "🏷  Grupo")
        self._horario_label = self._add_dato(insc_card, 3, "🕐  Horario")
        self._inscripcion_label = self._add_dato(insc_card, 4, "📅  Fecha de inscripción")
        ctk.CTkLabel(insc_card, text="", height=6).grid(row=5, column=0)

        # ── Acciones (gated por rol) ──────────────────────────
        self._actions_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._actions_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self._actions_frame.grid_columnconfigure(0, weight=1)

    def _add_dato(self, parent, row, etiqueta):
        cont = ctk.CTkFrame(parent, fg_color="transparent")
        cont.grid(row=row, column=0, columnspan=2, sticky="ew", padx=20, pady=6)
        cont.grid_columnconfigure(1, weight=1)
        make_label(cont, etiqueta, variant="label", width=190, anchor="w"
                   ).grid(row=0, column=0, sticky="w")
        valor = make_label(cont, "—", variant="body")
        valor.grid(row=0, column=1, sticky="w", padx=(16, 0))
        return valor

    @staticmethod
    def _texto_nacimiento(valor) -> str:
        """Fecha de nacimiento con la edad calculada, ej. '2012-05-10 (13 años)'."""
        if not valor:
            return "—"
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            return valor
        hoy = date.today()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        return f"{valor}  ({edad} año{'s' if edad != 1 else ''})"

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    @property
    def id_actual(self):
        """id_alumno que se está mostrando, o None."""
        return self._alumno.get("id_alumno")

    def cargar(self, alumno: dict):
        """Carga los datos del alumno y arma las acciones según el rol y estado."""
        self._alumno = alumno or {}
        es_activo = self._alumno.get("estado", "activo") == "activo"

        nombre = f"{self._alumno.get('nombre', '')} {self._alumno.get('apellido', '')}".strip()
        self._nombre_label.configure(text=nombre or "—")
        self._dni_label.configure(text=self._alumno.get("dni") or "—")
        self._nacimiento_label.configure(
            text=self._texto_nacimiento(self._alumno.get("fecha_nacimiento")))
        self._telefono_label.configure(text=self._alumno.get("telefono") or "—")
        self._tutor_label.configure(text=self._alumno.get("telefono_tutor") or "—")
        self._direccion_label.configure(text=self._alumno.get("direccion") or "—")

        grupo = self._alumno.get("nombre_grupo") or "—"
        if self._alumno.get("estado_grupo") and self._alumno["estado_grupo"] != "activo":
            grupo += "  (grupo inactivo)"
        self._grupo_label.configure(text=grupo)
        self._horario_label.configure(text=self._alumno.get("horario") or "—")
        self._inscripcion_label.configure(text=self._alumno.get("fecha_inscripcion") or "—")

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
            make_label(self._actions_frame,
                       "👁  Vista de solo lectura", variant="muted"
                       ).grid(row=0, column=0, sticky="w")
            return

        btn_row = ctk.CTkFrame(self._actions_frame, fg_color="transparent")
        btn_row.grid(row=0, column=0, sticky="e")

        # Igual que en el listado: un alumno inactivo se reactiva antes de editarse.
        if es_activo:
            make_button(btn_row, text="✏  Editar", variant="primary",
                        command=lambda: self._on_editar(self._alumno)
                        ).pack(side="left", padx=(0, 10))
            make_button(btn_row, text="🚫  Desactivar", variant="danger",
                        command=self._confirmar_desactivar).pack(side="left")
        else:
            make_button(btn_row, text="♻  Reactivar", variant="success",
                        command=self._confirmar_reactivar).pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Confirmaciones
    # ──────────────────────────────────────────────────────────
    def _nombre(self) -> str:
        return f"{self._alumno.get('nombre', '')} {self._alumno.get('apellido', '')}".strip()

    def _confirmar_desactivar(self):
        msg = CTkMessagebox(
            title="Desactivar alumno",
            message=f"¿Desactivar a {self._nombre()}?\n"
                    "Conserva todos sus datos e historial.",
            icon="question", option_1="Cancelar", option_2="Desactivar",
            button_color=COLORS["error"], button_hover_color="#C53030",
        )
        if msg.get() == "Desactivar":
            self._on_desactivar(self._alumno)

    def _confirmar_reactivar(self):
        msg = CTkMessagebox(
            title="Reactivar alumno",
            message=f"¿Reactivar a {self._nombre()}?",
            icon="question", option_1="Cancelar", option_2="Reactivar",
            button_color=COLORS["success"], button_hover_color="#2F855A",
        )
        if msg.get() == "Reactivar":
            self._on_reactivar(self._alumno)
