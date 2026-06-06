"""
Flamingo Sys — Gestión Integral Voley
views/grupos_form.py — Formulario de Alta de Grupo (HU01 / KAN-24)
"""

import customtkinter as ctk
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card, make_divider


class GruposFormView(ctk.CTkFrame):
    """
    Formulario para dar de alta un grupo.

    Parámetros:
        parent       : frame contenedor
        on_cancelar  : callback() al presionar Cancelar
        on_registrar : callback(datos_dict) al confirmar

    Campos: nombre (texto libre), horario (texto), descripción (texto).
    Validación en tiempo real: resalta en rojo los obligatorios vacíos y
    mantiene el botón 'Guardar' deshabilitado mientras falten.
    """

    # Campos obligatorios para habilitar el guardado
    _REQUERIDOS = ("nombre", "horario")

    def __init__(self, parent, on_cancelar, on_registrar):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_cancelar = on_cancelar
        self._on_registrar = on_registrar
        self._campos = {}
        self._errores = {}
        self._modo_edicion = False
        self._current_id = None
        self._originales = {}

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

        self._titulo_label = make_label(header, "➕  Nuevo Grupo", variant="h2")
        self._titulo_label.grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        self._subtitulo_label = make_label(
            header,
            "Completá los datos para registrar un nuevo grupo en el sistema.",
            variant="muted")
        self._subtitulo_label.grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        # ── Cuerpo scrollable ─────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0,
                                      scrollbar_button_color=COLORS["primary"],
                                      scrollbar_button_hover_color=COLORS["primary_hover"])
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        card = make_card(body)
        card.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        card.grid_columnconfigure(0, weight=1)

        make_label(card, "Datos del grupo", variant="h3"
                   ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 12))
        make_divider(card).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        self._add_field(card, 2, "nombre", "🏷  Nombre del grupo *",
                        "Ej: Sub-15 Competitivo")
        self._add_field(card, 3, "horario", "🕐  Horario *",
                        "Ej: Lunes y Miércoles 18:00")
        self._add_field(card, 4, "descripcion", "📝  Descripción",
                        "Ej: De 13 a 15 años (opcional)")

        # ── Error general (ej. nombre duplicado) ──────────────
        self._error_general = make_label(card, "", variant="error")
        self._error_general.grid(row=5, column=0, sticky="w", padx=20, pady=(0, 4))

        # ── Botones ───────────────────────────────────────────
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=6, column=0, sticky="e", padx=20, pady=(8, 24))

        make_button(btn_frame, text="Cancelar", variant="secondary",
                    command=self._on_cancelar,
                    ).pack(side="left", padx=(0, 10))

        self._submit_btn = make_button(btn_frame, text="  ✔  Registrar Grupo",
                                       variant="primary", command=self._do_submit)
        self._submit_btn.pack(side="left")

        self._refrescar_estado_submit()

    # ──────────────────────────────────────────────────────────
    # Helpers de campos
    # ──────────────────────────────────────────────────────────
    def _add_field(self, parent, row, campo_id, label, placeholder):
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=0, sticky="ew", padx=20, pady=6)
        container.grid_columnconfigure(0, weight=1)

        make_label(container, label, variant="label").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        entry = make_entry(container, placeholder=placeholder)
        entry.grid(row=1, column=0, sticky="ew")
        entry.bind("<KeyRelease>", lambda e, cid=campo_id: self._on_field_change(cid))
        entry.bind("<FocusOut>",   lambda e, cid=campo_id: self._validate_field(cid))

        err = make_label(container, "", variant="error")
        err.grid(row=2, column=0, sticky="w")

        self._campos[campo_id] = entry
        self._errores[campo_id] = err

    # ──────────────────────────────────────────────────────────
    # Validación
    # ──────────────────────────────────────────────────────────
    def _on_field_change(self, campo_id):
        """Al tipear: limpia el error general y revalida estado del botón."""
        self._error_general.configure(text="")
        if campo_id in self._REQUERIDOS:
            self._validate_field(campo_id)
        self._refrescar_estado_submit()

    def _validate_field(self, campo_id) -> bool:
        """Valida un campo obligatorio; lo resalta en rojo si está vacío."""
        if campo_id not in self._REQUERIDOS:
            return True

        entry = self._campos[campo_id]
        err_label = self._errores[campo_id]
        valor = entry.get().strip()

        if not valor:
            etiqueta = "El nombre" if campo_id == "nombre" else "El horario"
            entry.configure(border_color=COLORS["error"], border_width=2)
            err_label.configure(text=f"⚠  {etiqueta} es obligatorio")
            return False

        entry.configure(border_color=COLORS["border"], border_width=2)
        err_label.configure(text="")
        return True

    def _hay_requeridos_completos(self) -> bool:
        return all(self._campos[c].get().strip() for c in self._REQUERIDOS)

    def _hay_cambios(self) -> bool:
        """En edición: True solo si algún campo difiere del valor original."""
        return any(
            self._campos[cid].get().strip() != (orig or "")
            for cid, orig in self._originales.items()
        )

    def _refrescar_estado_submit(self):
        """
        Habilita 'Guardar' si los obligatorios están completos. En modo
        edición exige además que haya cambios reales (dirty checking).
        """
        habilitar = self._hay_requeridos_completos()
        if self._modo_edicion:
            habilitar = habilitar and self._hay_cambios()

        if habilitar:
            self._submit_btn.configure(state="normal",
                                       fg_color=COLORS["primary"],
                                       hover_color=COLORS["primary_hover"])
        else:
            self._submit_btn.configure(state="disabled",
                                       fg_color="#CCCCCC", hover_color="#AAAAAA")

    # ──────────────────────────────────────────────────────────
    # Submit / API pública
    # ──────────────────────────────────────────────────────────
    def _do_submit(self):
        validos = [self._validate_field(c) for c in self._REQUERIDOS]
        if not all(validos):
            return

        datos = {
            "id_grupo":    self._current_id,
            "nombre":      self._campos["nombre"].get().strip(),
            "horario":     self._campos["horario"].get().strip(),
            "descripcion": self._campos["descripcion"].get().strip(),
        }
        self._on_registrar(datos)

    def mostrar_error(self, mensaje: str):
        """Muestra un error devuelto por el backend (ej. nombre duplicado)."""
        self._error_general.configure(text=f"⚠  {mensaje}")
        # Si es por el nombre, lo resaltamos
        self._campos["nombre"].configure(border_color=COLORS["error"], border_width=2)

    def cargar_grupo(self, grupo: dict):
        """Precarga el formulario para editar un grupo existente (KAN-27)."""
        self._modo_edicion = True
        self._current_id = grupo.get("id_grupo")
        self._titulo_label.configure(text="✏  Editar Grupo")
        self._subtitulo_label.configure(
            text="Modificá los datos del grupo. El botón se habilita solo si hay cambios.")
        self._submit_btn.configure(text="  ✔  Guardar Cambios")
        self._error_general.configure(text="")

        valores = {
            "nombre":      grupo.get("nombre_grupo", ""),
            "horario":     grupo.get("horario", ""),
            "descripcion": grupo.get("descripcion") or "",
        }
        for campo_id, valor in valores.items():
            entry = self._campos[campo_id]
            entry.delete(0, "end")
            entry.insert(0, valor)
            entry.configure(border_color=COLORS["border"], border_width=2)
            self._errores[campo_id].configure(text="")

        # Guardamos los originales para el dirty checking
        self._originales = dict(valores)
        self._refrescar_estado_submit()

    def limpiar(self):
        """Resetea el formulario al estado de alta (Nuevo Grupo)."""
        self._modo_edicion = False
        self._current_id = None
        self._originales = {}
        self._titulo_label.configure(text="➕  Nuevo Grupo")
        self._subtitulo_label.configure(
            text="Completá los datos para registrar un nuevo grupo en el sistema.")
        self._submit_btn.configure(text="  ✔  Registrar Grupo")
        self._error_general.configure(text="")
        for campo_id, entry in self._campos.items():
            entry.delete(0, "end")
            entry.configure(border_color=COLORS["border"], border_width=2)
            self._errores[campo_id].configure(text="")
        self._refrescar_estado_submit()
