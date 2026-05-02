"""
Flamingo Sys — Gestión Integral Voley
main.py — Punto de entrada de la aplicación

Maneja la ventana principal y la navegación entre pantallas
mediante ocultamiento/mostrado de frames (sin destruir ventanas).
"""

import customtkinter as ctk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Design system centralizado ────────────────────────────────────
from theme import COLORS

# ── Vistas ────────────────────────────────────────────────────────
from views.login import LoginView
from views.recuperar import RecuperarView
from views.dashboard import DashboardView
from views.usuarios_listado import UsuariosListadoView
from views.usuarios_form import UsuariosFormView
from views.perfil import PerfilView
from components.sidebar import Sidebar
from CTkMessagebox import CTkMessagebox
import services.auth as auth_service
import services.usuarios as user_service
from db.database import init_db


# Inicializar base de datos y migraciones
init_db()

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class FlamingoApp(ctk.CTk):
    """
    Ventana principal de Flamingo Sys.
    Controla el ciclo de vida de las vistas y el estado de sesión.
    """

    def __init__(self):
        super().__init__()

        self.title("Flamingo Sys — Gestión Integral Voley")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg"])
        self._center_window(1200, 720)

        # Estado de sesión
        # TODO: conectar con backend — autenticación real
        self.current_user = None

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.content_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.sidebar = None
        self.views = {}
        self._init_auth_views()
        self.show_view("login")

    # ──────────────────────────────────────────────────────────────
    # Inicialización de vistas
    # ──────────────────────────────────────────────────────────────
    def _init_auth_views(self):
        """Crea las vistas de login/recuperar (sin sidebar)."""
        self.views["login"] = LoginView(
            self,
            on_login=self._handle_login,
            on_recuperar=lambda: self.show_view("recuperar"),
        )
        self.views["recuperar"] = RecuperarView(
            self,
            on_back=lambda: self.show_view("login"),
        )

    def _init_main_views(self):
        """Crea las vistas principales (post-login) y el sidebar."""
        if self.sidebar is not None:
            return

        self.sidebar = Sidebar(
            self,
            user=self.current_user,
            on_navigate=self.show_view,
            width=210,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.views["dashboard"] = DashboardView(
            self.content_frame, user=self.current_user
        )
        self.views["usuarios_listado"] = UsuariosListadoView(
            self.content_frame,
            on_nuevo=self._handle_nuevo_usuario,
            on_editar=self._handle_editar_usuario,
        )
        self.views["usuarios_form"] = UsuariosFormView(
            self.content_frame,
            on_cancelar=lambda: self.show_view("usuarios_listado"),
            on_registrar=self._handle_registrar_usuario,
        )
        self.views["perfil"] = PerfilView(
            self.content_frame,
            user=self.current_user,
            on_guardado=self._handle_perfil_guardado,
        )

        for view in ["dashboard", "usuarios_listado", "usuarios_form", "perfil"]:
            self.views[view].grid(row=0, column=0, sticky="nsew")
            self.views[view].grid_remove()

    # ──────────────────────────────────────────────────────────────
    # Navegación
    # ──────────────────────────────────────────────────────────────
    def show_view(self, view_name: str):
        """Muestra la vista indicada y oculta las demás."""
        for name in ["login", "recuperar"]:
            if name in self.views:
                self.views[name].place_forget()

        for name in ["dashboard", "usuarios_listado", "usuarios_form", "perfil"]:
            if name in self.views:
                self.views[name].grid_remove()

        if view_name in ["login", "recuperar"]:
            if self.sidebar:
                self.sidebar.grid_remove()
            self.content_frame.grid_remove()
            self.views[view_name].place(relx=0, rely=0, relwidth=1, relheight=1)
        else:
            self.content_frame.grid(row=0, column=1, sticky="nsew")
            if self.sidebar:
                self.sidebar.grid(row=0, column=0, sticky="nsew")
                self.sidebar.set_active(view_name)
            if view_name in self.views:
                self.views[view_name].grid(row=0, column=0, sticky="nsew")

    # ──────────────────────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────────────────────
    def _handle_login(self, user_data: dict):
        """
        Callback ejecutado cuando el login es exitoso.
        TODO: conectar con backend — validar credenciales contra BD
        """
        self.current_user = user_data
        self._init_main_views()
        self.show_view("dashboard")

    def _handle_nuevo_usuario(self):
        self.views["usuarios_form"].limpiar()
        self.show_view("usuarios_form")

    def _handle_editar_usuario(self, usuario: dict):
        self.views["usuarios_form"].cargar_usuario(usuario)
        self.show_view("usuarios_form")

    def _handle_registrar_usuario(self, datos: dict):
        """Maneja la creación o edición de un usuario en la BD."""
        if self.views["usuarios_form"]._modo_edicion:
            # Edición
            id_u = datos.get("id_usuario")
            exito = user_service.editar_usuario(
                id_usuario=id_u,
                usuario=datos["dni"],
                nombre=datos["nombre"],
                apellido=datos["apellido"],
                email=datos["email"],
                rol=datos["rol"].lower(),
                contrasena=datos["password"]
            )
        else:
            # Nuevo
            id_u = user_service.crear_usuario(
                usuario=datos["dni"],
                nombre=datos["nombre"],
                apellido=datos["apellido"],
                email=datos["email"],
                contrasena=datos["password"] or "123456",
                rol=datos["rol"].lower()
            )
            exito = bool(id_u)

        if exito and datos.get("preguntas"):
            auth_service.guardar_preguntas_seguridad(id_u, datos["preguntas"])
        
        if exito:
            if "usuarios_listado" in self.views:
                self.views["usuarios_listado"].cargar_datos()
                self.views["usuarios_listado"]._render_rows(self.views["usuarios_listado"]._usuarios)
            self.show_view("usuarios_listado")
        else:
            CTkMessagebox(title="Error", message="No se pudo procesar la solicitud.", icon="cancel")

    def _handle_perfil_guardado(self, datos: dict):
        """Actualiza los datos del perfil en la BD."""
        if self.current_user:
            exito = user_service.editar_usuario(
                id_usuario=self.current_user["id_usuario"],
                usuario=datos.get("nombre"),
                contrasena=datos.get("password")
            )
            if exito:
                self.current_user.update(datos)
                if self.sidebar:
                    self.sidebar.update_user(self.current_user)
            else:
                 CTkMessagebox(title="Error", message="Error al actualizar perfil.", icon="cancel")

    def _handle_logout(self):
        """Cierra la sesión y limpia el estado."""
        auth_service.logout()
        self.current_user = None
        for name in ["dashboard", "usuarios_listado", "usuarios_form", "perfil"]:
            if name in self.views:
                self.views[name].destroy()
                del self.views[name]
        if self.sidebar:
            self.sidebar.destroy()
            self.sidebar = None
        self.show_view("login")

    # ──────────────────────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────────────────────
    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")


if __name__ == "__main__":
    app = FlamingoApp()
    app.mainloop()
