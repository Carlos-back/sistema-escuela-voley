"""
Flamingo Sys — Gestión Integral Voley
views/inscripciones_form.py — Formulario de Nueva Inscripción (Sprint 5, HU01)
"""

import customtkinter as ctk

from theme import COLORS, FONTS, RADIUS, make_button, make_card, make_divider, make_label
from services import inscripciones as insc_service

PLACEHOLDER_GRUPO = "Seleccioná un grupo"


class InscripcionesFormView(ctk.CTkFrame):
    """
    Formulario para inscribir un alumno activo en un grupo activo.

    - Período: año en curso o el siguiente.
    - Alumno: combo con búsqueda (filtra mientras se escribe).
    - Grupo: combo con el cupo ocupado de cada grupo en el período elegido,
      e indicador de lugares libres. Los grupos completos se ven marcados;
      si igual se elige uno, el servicio rechaza la inscripción.

    Parámetros:
        parent       : frame contenedor
        on_cancelar  : callback()
        on_registrar : callback(datos) con {id_alumno, id_grupo, periodo}
    """

    def __init__(self, parent, on_cancelar, on_registrar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_cancelar = on_cancelar
        self._on_registrar = on_registrar
        self._alumnos_map = {}   # etiqueta -> id_alumno
        self._grupos = {}        # etiqueta -> dict del grupo

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=2, sticky="ew")
        make_label(header, "➕  Nueva Inscripción", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Inscribí un alumno activo en un grupo para el período elegido.",
                   variant="muted").grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))
        make_label(header, "(*) Campos obligatorios", variant="caption"
                   ).grid(row=2, column=1, sticky="e", padx=28, pady=(0, 16))

        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        card = make_card(body)
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        card.grid_columnconfigure(0, weight=1)
        make_label(card, "Datos de la inscripción", variant="h3"
                   ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 12))
        make_divider(card).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        # ── Período ───────────────────────────────────────────
        cont = self._contenedor(card, 2, "📅  Período *")
        self._periodo_var = ctk.StringVar(value=str(insc_service.anio_actual()))
        ctk.CTkSegmentedButton(
            cont, values=[str(p) for p in insc_service.periodos_habilitados()],
            variable=self._periodo_var, font=FONTS.BASE(), height=38,
            selected_color=COLORS["primary"], selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["white"], text_color=COLORS["text_dark"],
            command=lambda _v: self._on_periodo_change(),
        ).grid(row=1, column=0, sticky="w")

        # ── Alumno (con búsqueda) ─────────────────────────────
        cont = self._contenedor(card, 3, "🎓  Alumno *")
        self._alumno_combo = ctk.CTkComboBox(
            cont, values=[], font=FONTS.BASE(), height=42, corner_radius=RADIUS.MD,
            border_color=COLORS["border"], fg_color=COLORS["white"],
            button_color=COLORS["primary"], button_hover_color=COLORS["primary_hover"],
            text_color=COLORS["text_dark"], dropdown_fg_color=COLORS["white"],
            dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"],
            command=lambda _v: self._refrescar_estado())
        self._alumno_combo.grid(row=1, column=0, sticky="ew")
        self._alumno_combo._entry.bind("<KeyRelease>", self._filtrar_alumnos)
        make_label(cont, "Escribí apellido, nombre o DNI para filtrar. Solo se listan "
                         "alumnos activos.", variant="caption"
                   ).grid(row=2, column=0, sticky="w")

        # ── Grupo + cupo ──────────────────────────────────────
        cont = self._contenedor(card, 4, "🏷  Grupo *")
        self._grupo_var = ctk.StringVar(value=PLACEHOLDER_GRUPO)
        self._grupo_menu = ctk.CTkOptionMenu(
            cont, variable=self._grupo_var, values=[PLACEHOLDER_GRUPO],
            font=FONTS.BASE(), height=42, corner_radius=RADIUS.MD,
            fg_color=COLORS["white"], button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"], text_color=COLORS["text_dark"],
            dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"],
            command=lambda _v: self._refrescar_estado())
        self._grupo_menu.grid(row=1, column=0, sticky="ew")
        self._cupo_label = make_label(cont, "", variant="caption")
        self._cupo_label.grid(row=2, column=0, sticky="w", pady=(4, 0))

        # ── Error general + botones ───────────────────────────
        self._error_general = make_label(card, "", variant="error")
        self._error_general.grid(row=5, column=0, sticky="w", padx=20, pady=(4, 4))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=6, column=0, sticky="e", padx=20, pady=(8, 24))
        make_button(btn_frame, text="Cancelar", variant="secondary",
                    command=self._on_cancelar).pack(side="left", padx=(0, 10))
        self._submit_btn = make_button(btn_frame, text="  ✔  Confirmar Inscripción",
                                       variant="primary", command=self._do_submit)
        self._submit_btn.pack(side="left")

    def _contenedor(self, parent, row, label):
        cont = ctk.CTkFrame(parent, fg_color="transparent")
        cont.grid(row=row, column=0, sticky="ew", padx=20, pady=8)
        cont.grid_columnconfigure(0, weight=1)
        make_label(cont, label, variant="label").grid(row=0, column=0, sticky="w", pady=(0, 4))
        return cont

    # ──────────────────────────────────────────────────────────
    # Datos
    # ──────────────────────────────────────────────────────────
    def _cargar_alumnos(self):
        self._alumnos_map = {
            f"{a['apellido']}, {a['nombre']} — DNI {a['dni']}": a["id_alumno"]
            for a in insc_service.obtener_alumnos_activos()
        }
        self._alumno_combo.configure(values=list(self._alumnos_map))
        self._alumno_combo.set("")

    def _filtrar_alumnos(self, _event=None):
        """Filtra el desplegable de alumnos con el texto escrito."""
        from db.database import normalizar_texto
        texto = normalizar_texto(self._alumno_combo.get().strip())
        coincidencias = [k for k in self._alumnos_map if texto in normalizar_texto(k)]
        self._alumno_combo.configure(values=coincidencias or ["Sin coincidencias"])
        self._refrescar_estado()

    def _cargar_grupos(self):
        """Carga los grupos activos con su ocupación en el período elegido."""
        seleccionado = self._grupo_actual()
        id_sel = seleccionado["id_grupo"] if seleccionado else None
        self._grupos = {}
        for g in insc_service.obtener_grupos_con_cupo(int(self._periodo_var.get())):
            libres = g["cupo_maximo"] - g["ocupados"]
            marca = "  (sin cupo)" if libres <= 0 else ""
            etiqueta = (f"{g['nombre_grupo']} — {g['horario']} · "
                        f"{g['ocupados']}/{g['cupo_maximo']}{marca}")
            self._grupos[etiqueta] = g
        self._grupo_menu.configure(values=list(self._grupos) or [PLACEHOLDER_GRUPO])
        etiqueta_sel = next((k for k, g in self._grupos.items() if g["id_grupo"] == id_sel),
                            PLACEHOLDER_GRUPO)
        self._grupo_var.set(etiqueta_sel)
        if not self._grupos:
            self._error_general.configure(text="⚠  No hay grupos activos para inscribir.")

    def _grupo_actual(self):
        return self._grupos.get(self._grupo_var.get())

    def _alumno_actual(self):
        return self._alumnos_map.get(self._alumno_combo.get())

    # ──────────────────────────────────────────────────────────
    # Estado del formulario
    # ──────────────────────────────────────────────────────────
    def _on_periodo_change(self):
        self._error_general.configure(text="")
        self._cargar_grupos()
        self._refrescar_estado()

    def _refrescar_estado(self):
        """Actualiza el indicador de cupo y habilita el botón si está todo completo."""
        self._error_general.configure(text="")
        grupo = self._grupo_actual()
        if grupo:
            libres = grupo["cupo_maximo"] - grupo["ocupados"]
            if libres <= 0:
                self._cupo_label.configure(
                    text=f"⛔  Sin cupo disponible: {grupo['ocupados']} de "
                         f"{grupo['cupo_maximo']} lugares ocupados.",
                    text_color=COLORS["error"])
            else:
                color = COLORS["warning"] if libres <= 2 else COLORS["success"]
                self._cupo_label.configure(
                    text=f"👥  {grupo['ocupados']} de {grupo['cupo_maximo']} lugares "
                         f"ocupados · quedan {libres}.", text_color=color)
        else:
            self._cupo_label.configure(text="")

        if self._alumno_actual() and grupo:
            self._submit_btn.configure(state="normal", fg_color=COLORS["primary"],
                                       hover_color=COLORS["primary_hover"])
        else:
            self._submit_btn.configure(state="disabled", fg_color="#CCCCCC",
                                       hover_color="#AAAAAA")

    def _do_submit(self):
        id_alumno, grupo = self._alumno_actual(), self._grupo_actual()
        if not (id_alumno and grupo):
            return
        self._on_registrar({"id_alumno": id_alumno, "id_grupo": grupo["id_grupo"],
                            "periodo": int(self._periodo_var.get())})

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def mostrar_error(self, mensaje: str):
        """Muestra el error del servicio y refresca la ocupación por si cambió."""
        self._cargar_grupos()
        self._refrescar_estado()
        self._error_general.configure(text=f"⚠  {mensaje}")

    def limpiar(self):
        """Deja el formulario vacío con los datos actualizados."""
        self._periodo_var.set(str(insc_service.anio_actual()))
        self._grupo_var.set(PLACEHOLDER_GRUPO)
        self._error_general.configure(text="")
        self._cargar_alumnos()
        self._cargar_grupos()
        self._refrescar_estado()
