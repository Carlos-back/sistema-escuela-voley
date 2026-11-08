"""
Flamingo Sys — Gestión Integral Voley
views/inscripciones_listado.py — Listado de Inscripciones (Sprint 5, HU02 / HU03)
"""

import datetime
from tkinter import filedialog

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from theme import COLORS, FONTS, RADIUS, make_badge, make_button, make_card, make_label
from services import inscripciones as insc_service
from services.grupos import listar_grupos
from views.anular_inscripcion_dialog import AnularInscripcionDialog


class InscripcionesListadoView(ctk.CTkFrame):
    """
    Listado de inscripciones con filtros por período, grupo y estado,
    búsqueda por alumno o DNI, contador y exportación a Excel (HU03).
    El administrador puede registrar (HU01) y anular (HU02) inscripciones;
    el profesor solo consulta.

    Parámetros:
        parent    : frame contenedor
        rol       : rol del usuario en sesión
        usuario   : usuario en sesión (para auditar las anulaciones)
        on_nueva  : callback() para abrir el formulario de inscripción
    """

    _COL_BASE = {
        "Alumno": 220,
        "DNI": 100,
        "Grupo": 160,
        "Período": 80,
        "Fecha": 100,
        "Estado": 110,
    }
    _COL_FLEX = "Alumno"

    _ESTADOS = {"Todos": None, "Vigentes": "vigente", "Anuladas": "anulada",
                "Finalizadas": "finalizada"}
    _BADGE_ESTADO = {"vigente": "success", "anulada": "error", "finalizada": "neutral"}
    _TODOS_GRUPOS = "Todos los grupos"
    _TODOS_PERIODOS = "Todos"

    def __init__(self, parent, rol, usuario, on_nueva):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._es_admin = (rol or "").lower() == "administrador"
        self._usuario = usuario
        self._on_nueva = on_nueva

        self._col_widths = dict(self._COL_BASE)
        self._col_widths["Acciones"] = 110 if self._es_admin else 20
        self._inscripciones = []
        self._grupos_map = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, columnspan=4, sticky="ew")
        make_label(header, "📋  Inscripciones", variant="h2"
                   ).grid(row=1, column=0, sticky="w", padx=28, pady=(16, 4))
        make_label(header, "Inscripción de alumnos a grupos por período, con control de cupo.",
                   variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=28, pady=(0, 16))

        self._export_btn = make_button(header, text="  ⬇  Exportar a Excel", variant="secondary",
                                       command=self._exportar_excel)
        self._export_btn.grid(row=1, column=2, rowspan=2, padx=(0, 12), pady=16)
        if self._es_admin:
            make_button(header, text="  ＋  Nueva Inscripción", variant="primary",
                        command=self._on_nueva
                        ).grid(row=1, column=3, rowspan=2, padx=(0, 28), pady=16)

        # ── Filtros: período, grupo, estado ───────────────────
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))

        make_label(filtros, "Período", variant="label").pack(side="left", padx=(0, 6))
        self._periodo_var = ctk.StringVar(value=str(insc_service.anio_actual()))
        self._periodo_menu = self._option_menu(filtros, self._periodo_var, width=100)
        self._periodo_menu.pack(side="left", padx=(0, 16))

        make_label(filtros, "Grupo", variant="label").pack(side="left", padx=(0, 6))
        self._grupo_var = ctk.StringVar(value=self._TODOS_GRUPOS)
        self._grupo_menu = self._option_menu(filtros, self._grupo_var, width=200)
        self._grupo_menu.pack(side="left", padx=(0, 16))

        self._estado_var = ctk.StringVar(value="Vigentes")
        ctk.CTkSegmentedButton(
            filtros, values=list(self._ESTADOS.keys()), variable=self._estado_var,
            font=FONTS.BASE(), height=36,
            selected_color=COLORS["primary"], selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["white"], text_color=COLORS["text_dark"],
            command=lambda _v: self._aplicar_filtros(),
        ).pack(side="left")

        # ── Búsqueda + contador ───────────────────────────────
        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 0))
        search_bar.grid_columnconfigure(0, weight=1)
        self._search_entry = ctk.CTkEntry(
            search_bar, placeholder_text="🔍  Buscar por alumno o DNI...",
            font=FONTS.BASE(), height=40, corner_radius=RADIUS.MD,
            border_color=COLORS["border"], fg_color=COLORS["white"],
            text_color=COLORS["text_dark"])
        self._search_entry.grid(row=0, column=0, sticky="ew")
        self._search_entry.bind("<KeyRelease>", lambda e: self._aplicar_filtros())
        self._stats_label = make_label(search_bar, "", variant="muted")
        self._stats_label.grid(row=0, column=1, padx=(16, 0))

        # ── Tabla ─────────────────────────────────────────────
        tabla = make_card(self)
        tabla.grid(row=3, column=0, sticky="nsew", padx=20, pady=12)
        tabla.grid_columnconfigure(0, weight=1)
        tabla.grid_rowconfigure(1, weight=1)
        self._build_header_row(tabla)
        self._scroll_area = ctk.CTkScrollableFrame(
            tabla, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_hover"])
        self._scroll_area.grid(row=1, column=0, sticky="nsew")
        self._scroll_area.grid_columnconfigure(0, weight=1)

        self._cargar_opciones()
        self._aplicar_filtros()

    def _option_menu(self, parent, variable, width):
        return ctk.CTkOptionMenu(
            parent, variable=variable, values=[variable.get()], width=width,
            font=FONTS.BASE(), height=36, corner_radius=RADIUS.MD,
            fg_color=COLORS["white"], button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"], text_color=COLORS["text_dark"],
            dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"],
            command=lambda _v: self._aplicar_filtros())

    def _cargar_opciones(self):
        """Llena los combos de período y grupo con los datos actuales."""
        periodos = [self._TODOS_PERIODOS] + [str(p) for p in insc_service.periodos_registrados()]
        self._periodo_menu.configure(values=periodos)
        if self._periodo_var.get() not in periodos:
            self._periodo_var.set(str(insc_service.anio_actual()))

        self._grupos_map = {g["nombre_grupo"]: g["id_grupo"]
                            for g in listar_grupos(incluir_inactivos=True)}
        self._grupo_menu.configure(values=[self._TODOS_GRUPOS] + list(self._grupos_map))
        if self._grupo_var.get() not in self._grupos_map:
            self._grupo_var.set(self._TODOS_GRUPOS)

    def _configurar_columnas(self, contenedor):
        for i, (col, w) in enumerate(self._col_widths.items()):
            contenedor.grid_columnconfigure(
                i, minsize=w, weight=(1 if col == self._COL_FLEX else 0))

    def _build_header_row(self, parent):
        hr = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=0)
        hr.grid(row=0, column=0, sticky="ew")
        self._configurar_columnas(hr)
        for i, (col, ancho) in enumerate(self._col_widths.items()):
            texto = col.upper() if (col != "Acciones" or self._es_admin) else ""
            cf = ctk.CTkFrame(hr, fg_color="transparent", width=ancho, height=32)
            cf.grid(row=0, column=i, padx=(20 if i == 0 else 4, 4), pady=5, sticky="ew")
            cf.pack_propagate(False)
            make_label(cf, texto, variant="overline", anchor="w"
                       ).pack(side="left", fill="x", expand=True)

    # ──────────────────────────────────────────────────────────
    # Filtros (HU03)
    # ──────────────────────────────────────────────────────────
    def _filtros_actuales(self):
        periodo = self._periodo_var.get()
        return {
            "periodo": None if periodo == self._TODOS_PERIODOS else int(periodo),
            "id_grupo": self._grupos_map.get(self._grupo_var.get()),
            "estado": self._ESTADOS.get(self._estado_var.get()),
            "busqueda": self._search_entry.get().strip(),
        }

    def _texto_filtros(self) -> str:
        f = self._filtros_actuales()
        partes = [f"Período {f['periodo'] or 'todos'}", self._grupo_var.get(),
                  self._estado_var.get()]
        if f["busqueda"]:
            partes.append(f"búsqueda \"{f['busqueda']}\"")
        return " · ".join(partes)

    def _aplicar_filtros(self):
        self._inscripciones = insc_service.listar_inscripciones(**self._filtros_actuales())
        n = len(self._inscripciones)
        self._stats_label.configure(text=f"  {n} resultado{'s' if n != 1 else ''}")
        self._export_btn.configure(state="normal" if n else "disabled")
        self._render_rows()

    def _render_rows(self):
        for widget in self._scroll_area.winfo_children():
            widget.destroy()
        if not self._inscripciones:
            make_label(self._scroll_area, "Sin resultados para la búsqueda realizada",
                       variant="muted").grid(row=0, column=0, pady=40)
            return
        for idx, insc in enumerate(self._inscripciones):
            self._build_data_row(idx, insc)

    def _ancho(self, col):
        return list(self._col_widths.values())[col]

    def _celda(self, row_f, col, texto, variant="body", primera=False):
        f = ctk.CTkFrame(row_f, fg_color="transparent", width=self._ancho(col), height=46)
        f.grid(row=0, column=col, padx=(20 if primera else 4, 4), pady=2, sticky="ew")
        f.pack_propagate(False)
        make_label(f, str(texto), variant=variant, anchor="w").pack(side="left", fill="x",
                                                                    expand=True)
        return f

    def _build_data_row(self, idx, insc):
        bg = COLORS["white"] if idx % 2 == 0 else "#FAFAFA"
        row_f = ctk.CTkFrame(self._scroll_area, fg_color=bg, corner_radius=0)
        row_f.grid(row=idx, column=0, sticky="ew")
        self._configurar_columnas(row_f)
        ctk.CTkFrame(row_f, height=1, fg_color=COLORS["border"],
                     corner_radius=0).place(relx=0, rely=1.0, relwidth=1, y=-1)

        alumno, dni, grupo, periodo, fecha, _estado = insc_service.fila_listado(insc)
        self._celda(row_f, 0, alumno, "bold", primera=True)
        self._celda(row_f, 1, dni)
        self._celda(row_f, 2, grupo, "muted")
        self._celda(row_f, 3, periodo)
        self._celda(row_f, 4, fecha, "muted")

        sf = ctk.CTkFrame(row_f, fg_color="transparent", width=self._ancho(5), height=46)
        sf.grid(row=0, column=5, padx=4, pady=2, sticky="ew")
        sf.pack_propagate(False)
        make_badge(sf, text=insc["estado"].capitalize(),
                   variant=self._BADGE_ESTADO.get(insc["estado"], "neutral")).pack(side="left")

        af = ctk.CTkFrame(row_f, fg_color="transparent", width=self._ancho(6), height=46)
        af.grid(row=0, column=6, padx=4, pady=2, sticky="ew")
        af.pack_propagate(False)
        # HU02: solo el administrador y solo sobre inscripciones vigentes
        if self._es_admin and insc["estado"] == "vigente":
            make_button(af, text="🚫 Anular", variant="ghost", size="sm",
                        border_color=COLORS["error"], border_width=1, width=90,
                        text_color=COLORS["error"],
                        command=lambda i=insc: self._abrir_anulacion(i)).pack(side="left")
        elif insc["estado"] == "anulada" and insc.get("motivo_anulacion"):
            make_label(af, insc["motivo_anulacion"], variant="caption", anchor="w"
                       ).pack(side="left")

    # ──────────────────────────────────────────────────────────
    # Acciones
    # ──────────────────────────────────────────────────────────
    def _abrir_anulacion(self, insc):
        AnularInscripcionDialog(self.winfo_toplevel(), insc, on_confirmar=self._anular)

    def _anular(self, insc, motivo, detalle):
        """Callback del diálogo. Retorna el mensaje de error o None si salió bien."""
        exito, mensaje = insc_service.anular_inscripcion(
            insc["id_inscripcion"], motivo, detalle, usuario=self._usuario)
        if not exito:
            return mensaje
        self.refrescar()
        CTkMessagebox(title="Inscripción anulada", message=mensaje, icon="check",
                      option_1="OK")
        return None

    def _exportar_excel(self):
        if not self._inscripciones:
            return
        nombre = f"inscripciones_{datetime.date.today():%Y%m%d}.xlsx"
        path = filedialog.asksaveasfilename(
            title="Exportar listado", defaultextension=".xlsx", initialfile=nombre,
            filetypes=[("Libro de Excel", "*.xlsx")])
        if not path:
            return
        exito, mensaje = insc_service.exportar_listado_excel(
            path, self._inscripciones, self._texto_filtros())
        CTkMessagebox(title="Exportar a Excel" if exito else "Atención",
                      message=f"{mensaje}\n{path}" if exito else mensaje,
                      icon="check" if exito else "warning", option_1="OK")

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def refrescar(self):
        """Recarga combos y datos respetando los filtros activos."""
        self._cargar_opciones()
        self._aplicar_filtros()
