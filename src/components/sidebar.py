"""
Flamingo Sys — Gestión Integral Voley
components/sidebar.py — Sidebar de navegación reutilizable
"""

import customtkinter as ctk
import threading
from theme import COLORS, FONTS
from db.sync import sincronizar, obtener_ultima_sincronizacion
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
        ("alumnos",          "Alumnos",          "🎓",  None),
        ("pagos",            "Pagos",            "💳",  None),
        ("usuarios_listado", "Gestión Usuarios", "👥",  ["administrador"]),
        ("perfil",           "Mi Perfil",        "👤",  None),
    ]

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

        self._build_ui()

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
        
        ultima_sync = obtener_ultima_sincronizacion()
        
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
            text=f"Última sync:\n{ultima_sync}", 
            font=FONTS.XS(), 
            text_color=COLORS["sidebar_text"],
            justify="center"
        )
        self.lbl_sync.pack()

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

    def _handle_sync(self):
        """Inicia el proceso de sincronización en un hilo secundario."""
        self.btn_sync.configure(state="disabled", text="☁  Sincronizando...")
        self.lbl_sync.configure(text="Por favor espere...")
        
        # Ejecutar en segundo plano
        thread = threading.Thread(target=self._run_sync_task)
        thread.daemon = True
        thread.start()
        
    def _run_sync_task(self):
        """Tarea que corre en background."""
        resultado = sincronizar()
        # Volver al hilo principal para actualizar la UI
        self.after(0, lambda: self._on_sync_finished(resultado))
        
    def _on_sync_finished(self, resultado: dict):
        """Actualiza la UI tras la sincronización."""
        self.btn_sync.configure(state="normal", text="☁  Sincronizar")
        
        if resultado.get("exito"):
            fecha = resultado.get("fecha")
            regs = resultado.get("registros_sincronizados", 0)
            self.lbl_sync.configure(text=f"Última sync:\n{fecha}")
            try:
                CTkMessagebox(
                    title="Sincronización Exitosa", 
                    message=f"Se sincronizaron {regs} registros correctamente a MongoDB Atlas.\n\nFecha: {fecha}", 
                    icon="check",
                    option_1="OK"
                )
            except Exception:
                pass
        else:
            error_msg = resultado.get("error", "Error desconocido")
            self.lbl_sync.configure(text=f"Error en sync")
            try:
                CTkMessagebox(
                    title="Error de Sincronización", 
                    message=f"No se pudo sincronizar.\nDetalle: {error_msg}", 
                    icon="cancel",
                    option_1="OK"
                )
            except Exception:
                pass
