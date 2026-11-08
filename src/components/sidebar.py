"""
Flamingo Sys — Gestión Integral Voley
components/sidebar.py — Sidebar de navegación reutilizable
"""

import customtkinter as ctk
import threading
from theme import COLORS, FONTS
from db.sync import sincronizar, obtener_ultima_sincronizacion, contar_pendientes
from CTkMessagebox import CTkMessagebox


class Sidebar(ctk.CTkFrame):
    """
    Sidebar de navegación lateral.

    Parámetros:
        parent      : widget padre
        user        : dict con datos del usuario actual
        on_navigate : callback(view_name) al hacer clic en un ítem
        width       : ancho fijo del sidebar (default 210)
    """

    MENU_ITEMS = [
        ("dashboard",        "Inicio",           "🏠",  None),
        ("grupos_listado",   "Grupos",           "🏷",  ["administrador", "profesor"]),
        ("alumnos_listado",  "Alumnos",          "🎓",  None),
        ("inscripciones_listado", "Inscripciones", "📋",  None),
        ("informe_ocupacion", "Informes",        "📊",  ["administrador"]),
        ("pagos",            "Pagos",            "💳",  None),
        ("usuarios_listado", "Gestión Usuarios", "👥",  ["administrador"]),
        ("perfil",           "Mi Perfil",        "👤",  None),
    ]

    REINTENTO_MS = 5 * 60 * 1000   # reintento automático cada 5 minutos

    def __init__(self, parent, user: dict, on_navigate, width: int = 210):
        super().__init__(
            parent,
            width=width,
            corner_radius=0,
            fg_color=COLORS["sidebar_bg"],
        )
        self.grid_propagate(False)
        self.configure(width=width)

        self._on_navigate = on_navigate
        self._user = user or {}
        self._active_view = None
        self._buttons = {}
        self._width = width
        self._sync_resultado = None   # resultado que deja el hilo de sincronización
        self._sync_en_curso = False
        self._sin_conexion = False

        self._build_ui()
        # HU05: al iniciar sesión se sincroniza en segundo plano si hay pendientes,
        # y se reintenta cada cierto tiempo mientras queden cambios sin subir.
        self.after(1500, lambda: self._iniciar_sync(automatica=True))
        self.after(self.REINTENTO_MS, self._reintento_periodico)

    # ──────────────────────────────────────────────────────────
    # Construcción de la UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # ── Franja de acento + logo ───────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(header, height=4, fg_color=COLORS["primary"],
                     corner_radius=0).grid(row=0, column=0, sticky="ew")

        logo_frame = ctk.CTkFrame(header, fg_color="transparent", corner_radius=0)
        logo_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(20, 4))

        ctk.CTkLabel(logo_frame, text="🦩",
                     font=FONTS.XXXL(), text_color=COLORS["primary"]).pack()

        ctk.CTkLabel(logo_frame, text="Flamingo Sys",
                     font=FONTS.MD_BOLD(), text_color="#FFFFFF").pack()

        ctk.CTkLabel(logo_frame, text="Gestión Integral · Voley",
                     font=FONTS.XS(), text_color=COLORS["sidebar_text"]).pack()

        # Separador
        ctk.CTkFrame(self, height=1, fg_color="#3D3D3D",
                     corner_radius=0).grid(row=1, column=0, sticky="ew",
                                           padx=12, pady=(14, 6))

        # ── Ítems de menú ─────────────────────────────────────
        menu_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        menu_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        menu_frame.grid_columnconfigure(0, weight=1)

        rol_actual = self._user.get("rol", "").lower()

        row_idx = 0
        for view_name, label, icon, roles in self.MENU_ITEMS:
            if roles and rol_actual not in roles:
                continue
            btn = self._make_nav_button(menu_frame, view_name, label, icon)
            btn.grid(row=row_idx, column=0, sticky="ew", pady=2)
            self._buttons[view_name] = btn
            row_idx += 1

        self.grid_rowconfigure(3, weight=1)

        # ── Sección de sincronización ─────────────────────────
        self.sync_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sync_frame.grid(row=3, column=0, sticky="s", padx=8, pady=(0, 10))

        self.btn_sync = ctk.CTkButton(
            self.sync_frame,
            text="☁  Sincronizar",
            font=FONTS.BASE_BOLD(),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            height=36,
            corner_radius=8,
            command=self._handle_sync
        )
        self.btn_sync.pack(fill="x", pady=(0, 4))

        self.lbl_sync = ctk.CTkLabel(
            self.sync_frame,
            text="",
            font=FONTS.XS(),
            text_color=COLORS["sidebar_text"],
            justify="center"
        )
        self.lbl_sync.pack()
        self.refrescar_estado_sync()

        # ── Sección inferior: usuario + logout ─────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        bottom.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 12))
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(bottom, height=1, fg_color="#3D3D3D",
                     corner_radius=0).grid(row=0, column=0, sticky="ew",
                                           padx=4, pady=(0, 10))

        # Card de usuario
        nombre = self._user.get("nombre", "Usuario")
        rol_display = self._user.get("rol", "").capitalize()

        user_card = ctk.CTkFrame(bottom, fg_color="#353535", corner_radius=10)
        user_card.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        user_card.grid_columnconfigure(1, weight=1)

        # Avatar circular con inicial
        avatar = ctk.CTkFrame(user_card, width=34, height=34,
                              corner_radius=17, fg_color=COLORS["primary"])
        avatar.grid(row=0, column=0, padx=(10, 8), pady=10, rowspan=2)
        avatar.grid_propagate(False)
        ctk.CTkLabel(avatar,
                     text=nombre[0].upper() if nombre else "U",
                     font=FONTS.MD_BOLD(), text_color="white"
                     ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(user_card, text=nombre,
                     font=FONTS.BASE_BOLD(), text_color="#FFFFFF",
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(10, 0))

        ctk.CTkLabel(user_card, text=rol_display,
                     font=FONTS.XS(), text_color=COLORS["sidebar_text"],
                     anchor="w").grid(row=1, column=1, sticky="w", pady=(0, 10))

        # Botón Cerrar Sesión
        ctk.CTkButton(
            bottom,
            text="🚪  Cerrar Sesión",
            font=FONTS.BASE(),
            fg_color="transparent",
            hover_color="#3D0010",
            text_color="#FF6B6B",
            anchor="w",
            height=36,
            corner_radius=8,
            command=self._on_logout,
        ).grid(row=2, column=0, sticky="ew", padx=4)

    def _make_nav_button(self, parent, view_name: str,
                         label: str, icon: str) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=f"  {icon}  {label}",
            font=FONTS.BASE(),
            fg_color="transparent",
            hover_color=COLORS["sidebar_hover"],
            text_color=COLORS["sidebar_text"],
            anchor="w",
            height=42,
            corner_radius=8,
            command=lambda v=view_name: self._navigate(v),
        )

    # ──────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────
    def set_active(self, view_name: str):
        """Resalta el ítem activo en fucsia."""
        self._active_view = view_name
        for name, btn in self._buttons.items():
            if name == view_name:
                btn.configure(fg_color=COLORS["primary"],
                              text_color="#FFFFFF",
                              hover_color=COLORS["primary_hover"])
            else:
                btn.configure(fg_color="transparent",
                              text_color=COLORS["sidebar_text"],
                              hover_color=COLORS["sidebar_hover"])

    def update_user(self, user: dict):
        """
        Actualiza info del usuario en el sidebar.
        TODO: conectar con backend — refrescar datos de sesión
        """
        self._user = user or {}
        for widget in self.winfo_children():
            widget.destroy()
        self._buttons.clear()
        self._build_ui()
        if self._active_view:
            self.set_active(self._active_view)

    # ──────────────────────────────────────────────────────────
    # Callbacks privados
    # ──────────────────────────────────────────────────────────
    def _navigate(self, view_name: str):
        self._on_navigate(view_name)

    def _on_logout(self):
        """TODO: conectar con backend — invalidar sesión/token"""
        root = self.winfo_toplevel()
        if hasattr(root, "_handle_logout"):
            root._handle_logout()

    # ──────────────────────────────────────────────────────────
    # Sincronización con la nube (HU05)
    # ──────────────────────────────────────────────────────────
    def refrescar_estado_sync(self):
        """Muestra la última sincronización y los cambios pendientes."""
        if self._sync_en_curso or not self.winfo_exists():
            return
        pendientes = contar_pendientes()
        if self._sin_conexion and pendientes:
            texto = f"Sin conexión – {pendientes} cambios pendientes"
            color = COLORS["warning"]
        elif pendientes:
            texto = (f"Última sync: {obtener_ultima_sincronizacion()}\n"
                     f"{pendientes} cambio{'s' if pendientes != 1 else ''} pendiente"
                     f"{'s' if pendientes != 1 else ''}")
            color = COLORS["warning"]
        else:
            texto = f"Última sync: {obtener_ultima_sincronizacion()}\n✔ Todo sincronizado"
            color = COLORS["sidebar_text"]
        self.lbl_sync.configure(text=texto, text_color=color)

    def _handle_sync(self):
        """Sincronización manual (botón)."""
        self._iniciar_sync(automatica=False)

    def _iniciar_sync(self, automatica: bool):
        """Lanza la sincronización en un hilo para no bloquear la pantalla."""
        if self._sync_en_curso or not self.winfo_exists():
            return
        if automatica and contar_pendientes() == 0:
            return
        self._sync_en_curso = True
        self._sync_resultado = None
        self.btn_sync.configure(state="disabled", text="☁  Sincronizando...")
        self.lbl_sync.configure(text="Subiendo cambios a la nube...",
                                text_color=COLORS["sidebar_text"])

        def tarea():
            self._sync_resultado = sincronizar(automatica=automatica)

        threading.Thread(target=tarea, daemon=True).start()
        self.after(300, lambda: self._esperar_sync(automatica))

    def _esperar_sync(self, automatica: bool):
        """Consulta desde el hilo principal si el hilo de sync terminó."""
        if not self.winfo_exists():
            return
        if self._sync_resultado is None:
            self.after(300, lambda: self._esperar_sync(automatica))
            return
        self._on_sync_finished(self._sync_resultado, automatica)

    def _reintento_periodico(self):
        if not self.winfo_exists():
            return
        self._iniciar_sync(automatica=True)
        self.after(self.REINTENTO_MS, self._reintento_periodico)

    def _on_sync_finished(self, resultado: dict, automatica: bool = False):
        """Actualiza la UI tras la sincronización."""
        self._sync_en_curso = False
        self._sin_conexion = bool(resultado.get("sin_conexion"))
        self.btn_sync.configure(state="normal", text="☁  Sincronizar")
        self.refrescar_estado_sync()

        # La automática no interrumpe con ventanas: solo actualiza el estado.
        if automatica:
            return
        if resultado.get("exito"):
            regs = resultado.get("registros_sincronizados", 0)
            mensaje = (f"Se subieron {regs} registros a MongoDB Atlas."
                       if regs else "No había cambios pendientes: la nube ya está al día.")
            CTkMessagebox(title="Sincronización exitosa",
                          message=f"{mensaje}\n\nFecha: {resultado.get('fecha')}",
                          icon="check", option_1="OK")
        else:
            pendientes = resultado.get("pendientes", 0)
            CTkMessagebox(title="No se pudo sincronizar",
                          message=f"{resultado.get('error', 'Error desconocido')}.\n\n"
                                  f"Cambios pendientes: {pendientes}. "
                                  "Se reintentará automáticamente.",
                          icon="warning", option_1="OK")
