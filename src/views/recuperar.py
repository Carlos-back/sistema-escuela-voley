"""
Flamingo Sys — Gestión Integral Voley
views/recuperar.py — Pantalla de recuperación de contraseña (3 Pasos)
"""

import customtkinter as ctk
import re
from theme import COLORS, FONTS, RADIUS, make_button, make_entry, make_label, make_card
from services.auth import obtener_preguntas, verificar_respuestas, resetear_contrasena

class RecuperarView(ctk.CTkFrame):
    """
    Vista de recuperación de contraseña en 3 pasos.
    """

    def __init__(self, parent, on_back):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._on_back = on_back
        
        self.dni_actual = None
        self.preguntas_actuales = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_ui()

    def _build_ui(self):
        # ── Panel izquierdo decorativo ─────────────────────────
        left = ctk.CTkFrame(self, fg_color=COLORS["sidebar_bg"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.grid(row=0, column=0)

        ctk.CTkLabel(inner, text="🦩", font=FONTS.XXXL()).pack(pady=(0, 12))
        make_label(inner, "Flamingo Sys", variant="h1", text_color=COLORS["primary"]).pack()
        make_label(inner, "Gestión Integral · Voley", text_color=COLORS["sidebar_text"]).pack(pady=(4, 0))

        ctk.CTkFrame(inner, height=3, width=100, fg_color=COLORS["primary"], corner_radius=2).pack(pady=(20, 0))

        make_label(inner, "Recuperación segura de acceso.\nPor favor, completá los pasos.", variant="muted", justify="center").pack(pady=(14, 0))

        # ── Panel derecho (formulario) ─────────────────────────
        self.right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.grid_columnconfigure(0, weight=1)
        self.right.grid_rowconfigure(0, weight=1)

        self.card = make_card(self.right)
        self.card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.72)
        self.card.grid_columnconfigure(0, weight=1)
        
        # Frames para los 3 pasos
        self.step1_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.step2_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.step3_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        
        for frame in (self.step1_frame, self.step2_frame, self.step3_frame):
            frame.grid_columnconfigure(0, weight=1)
            
        self._build_step1()
        self._build_step2()
        self._build_step3()
        
        # Ocultar paso 2 y 3
        self.show_step(1)

    def show_step(self, step):
        self.step1_frame.grid_remove()
        self.step2_frame.grid_remove()
        self.step3_frame.grid_remove()
        
        if step == 1:
            self.step1_frame.grid(row=0, column=0, sticky="nsew", pady=20)
            self._dni_entry.focus()
        elif step == 2:
            self.step2_frame.grid(row=0, column=0, sticky="nsew", pady=20)
            self._resp1_entry.focus()
        elif step == 3:
            self.step3_frame.grid(row=0, column=0, sticky="nsew", pady=20)
            self._pw_entry.focus()

    # ──────────────────────────────────────────────────────────
    # PASO 1: Ingreso de DNI
    # ──────────────────────────────────────────────────────────
    def _build_step1(self):
        ctk.CTkLabel(self.step1_frame, text="🔑", font=FONTS.XXXL()).grid(row=0, column=0, pady=(16, 8))
        make_label(self.step1_frame, "Recuperar Contraseña", variant="h2").grid(row=1, column=0, padx=36)
        make_label(self.step1_frame, "Paso 1: Ingresá tu DNI para comenzar.", variant="muted", justify="center").grid(row=2, column=0, padx=36, pady=(6, 24))

        make_label(self.step1_frame, "🪪  DNI", variant="label").grid(row=3, column=0, sticky="w", padx=36, pady=(0, 4))
        
        self._dni_entry = make_entry(self.step1_frame, placeholder="Tu número de documento")
        self._dni_entry.grid(row=4, column=0, sticky="ew", padx=36, pady=(0, 4))
        self._dni_entry.bind("<Return>", lambda e: self._verify_step1())
        
        self._dni_error = make_label(self.step1_frame, "", variant="error")
        self._dni_error.grid(row=5, column=0, sticky="w", padx=36, pady=(0, 8))

        self._s1_btn = make_button(self.step1_frame, text="  Siguiente  →", variant="primary", size="lg", command=self._verify_step1)
        self._s1_btn.grid(row=6, column=0, sticky="ew", padx=36, pady=(4, 12))

        make_button(self.step1_frame, text="← Volver al inicio de sesión", variant="ghost", font=ctk.CTkFont(size=12, underline=True), command=self._on_back).grid(row=7, column=0, pady=(0, 10))

    def _verify_step1(self):
        dni = self._dni_entry.get().strip()
        if not dni:
            self._set_error(self._dni_entry, self._dni_error, "Por favor ingresá un DNI válido.")
            return
            
        preguntas = obtener_preguntas(dni)
        if not preguntas:
            self._set_error(self._dni_entry, self._dni_error, "Usuario no encontrado o no tiene preguntas configuradas.")
            return
            
        self.dni_actual = dni
        self.preguntas_actuales = preguntas
        
        # Cargar preguntas en el paso 2
        self._q1_label.configure(text=f"1. {preguntas[0]}")
        self._q2_label.configure(text=f"2. {preguntas[1]}")
        self._q3_label.configure(text=f"3. {preguntas[2]}")
        
        # Resetear errores
        self._clear_error(self._dni_entry, self._dni_error)
        self.show_step(2)

    # ──────────────────────────────────────────────────────────
    # PASO 2: Preguntas de Seguridad
    # ──────────────────────────────────────────────────────────
    def _build_step2(self):
        ctk.CTkLabel(self.step2_frame, text="🛡", font=FONTS.XXXL()).grid(row=0, column=0, pady=(0, 8))
        make_label(self.step2_frame, "Preguntas de Seguridad", variant="h2").grid(row=1, column=0, padx=36)
        make_label(self.step2_frame, "Paso 2: Respondé a las siguientes preguntas.", variant="muted", justify="center").grid(row=2, column=0, padx=36, pady=(6, 16))

        # Pregunta 1
        self._q1_label = make_label(self.step2_frame, "1. Pregunta", variant="label", wraplength=400)
        self._q1_label.grid(row=3, column=0, sticky="w", padx=36, pady=(0, 4))
        self._resp1_entry = make_entry(self.step2_frame, placeholder="Tu respuesta")
        self._resp1_entry.grid(row=4, column=0, sticky="ew", padx=36, pady=(0, 12))
        
        # Pregunta 2
        self._q2_label = make_label(self.step2_frame, "2. Pregunta", variant="label", wraplength=400)
        self._q2_label.grid(row=5, column=0, sticky="w", padx=36, pady=(0, 4))
        self._resp2_entry = make_entry(self.step2_frame, placeholder="Tu respuesta")
        self._resp2_entry.grid(row=6, column=0, sticky="ew", padx=36, pady=(0, 12))
        
        # Pregunta 3
        self._q3_label = make_label(self.step2_frame, "3. Pregunta", variant="label", wraplength=400)
        self._q3_label.grid(row=7, column=0, sticky="w", padx=36, pady=(0, 4))
        self._resp3_entry = make_entry(self.step2_frame, placeholder="Tu respuesta")
        self._resp3_entry.grid(row=8, column=0, sticky="ew", padx=36, pady=(0, 4))
        
        self._resp3_entry.bind("<Return>", lambda e: self._verify_step2())

        self._s2_error = make_label(self.step2_frame, "", variant="error")
        self._s2_error.grid(row=9, column=0, sticky="w", padx=36, pady=(0, 8))

        btn_row = ctk.CTkFrame(self.step2_frame, fg_color="transparent")
        btn_row.grid(row=10, column=0, sticky="ew", padx=36, pady=(4, 12))
        btn_row.grid_columnconfigure(1, weight=1)
        
        make_button(btn_row, text="← Atrás", variant="secondary", command=lambda: self.show_step(1)).grid(row=0, column=0, padx=(0, 10))
        make_button(btn_row, text="Verificar  ✔", variant="primary", command=self._verify_step2).grid(row=0, column=1, sticky="ew")

    def _verify_step2(self):
        r1 = self._resp1_entry.get().strip()
        r2 = self._resp2_entry.get().strip()
        r3 = self._resp3_entry.get().strip()
        
        if not r1 or not r2 or not r3:
            self._s2_error.configure(text="⚠  Completá todas las respuestas.")
            return
            
        exito = verificar_respuestas(self.dni_actual, [r1, r2, r3])
        if exito:
            self._s2_error.configure(text="")
            self.show_step(3)
        else:
            self._s2_error.configure(text="⚠  Respuestas incorrectas, intente nuevamente.")
            for e in [self._resp1_entry, self._resp2_entry, self._resp3_entry]:
                e.configure(border_color=COLORS["error"])

    # ──────────────────────────────────────────────────────────
    # PASO 3: Nueva Contraseña
    # ──────────────────────────────────────────────────────────
    def _build_step3(self):
        ctk.CTkLabel(self.step3_frame, text="🔒", font=FONTS.XXXL()).grid(row=0, column=0, pady=(0, 8))
        make_label(self.step3_frame, "Nueva Contraseña", variant="h2").grid(row=1, column=0, padx=36)
        make_label(self.step3_frame, "Paso 3: Creá tu nueva contraseña.", variant="muted", justify="center").grid(row=2, column=0, padx=36, pady=(6, 16))

        # Contraseña
        make_label(self.step3_frame, "🔒 Nueva Contraseña", variant="label").grid(row=3, column=0, sticky="w", padx=36, pady=(0, 4))
        
        pw_row = ctk.CTkFrame(self.step3_frame, fg_color="transparent")
        pw_row.grid(row=4, column=0, sticky="ew", padx=36, pady=(0, 12))
        pw_row.grid_columnconfigure(0, weight=1)
        
        self._pw_entry = make_entry(pw_row, placeholder="Mínimo 6 chars, 1 alfanumérico, 2 mayúsc.", show="●")
        self._pw_entry.grid(row=0, column=0, sticky="ew")
        
        self._show_pw = False
        self._pw_toggle = ctk.CTkButton(
            pw_row, text="👁", width=42, height=42, corner_radius=RADIUS.MD,
            fg_color=COLORS["border"], hover_color="#D1D5DB", text_color=COLORS["text_dark"],
            command=self._toggle_password
        )
        self._pw_toggle.grid(row=0, column=1, padx=(8, 0))
        
        # Confirmar
        make_label(self.step3_frame, "🔁 Confirmar Contraseña", variant="label").grid(row=5, column=0, sticky="w", padx=36, pady=(0, 4))
        self._conf_entry = make_entry(self.step3_frame, placeholder="Repetí la contraseña", show="●")
        self._conf_entry.grid(row=6, column=0, sticky="ew", padx=36, pady=(0, 4))
        
        self._conf_entry.bind("<Return>", lambda e: self._verify_step3())

        self._s3_error = make_label(self.step3_frame, "", variant="error")
        self._s3_error.grid(row=7, column=0, sticky="w", padx=36, pady=(0, 8))
        
        self._s3_success = make_label(self.step3_frame, "", variant="success")
        self._s3_success.grid(row=8, column=0, sticky="w", padx=36, pady=(0, 8))

        btn_row = ctk.CTkFrame(self.step3_frame, fg_color="transparent")
        btn_row.grid(row=9, column=0, sticky="ew", padx=36, pady=(4, 12))
        btn_row.grid_columnconfigure(0, weight=1)
        
        self._s3_btn = make_button(btn_row, text="Guardar Contraseña  ✔", variant="primary", size="lg", command=self._verify_step3)
        self._s3_btn.grid(row=0, column=0, sticky="ew")

    def _toggle_password(self):
        self._show_pw = not self._show_pw
        self._pw_entry.configure(show="" if self._show_pw else "●")
        self._conf_entry.configure(show="" if self._show_pw else "●")
        self._pw_toggle.configure(text="🙈" if self._show_pw else "👁")

    def _verify_step3(self):
        pw = self._pw_entry.get()
        conf = self._conf_entry.get()
        
        if not pw or not conf:
            self._set_error(self._pw_entry, self._s3_error, "Ambos campos son obligatorios.")
            self._conf_entry.configure(border_color=COLORS["error"])
            return
            
        if pw != conf:
            self._set_error(self._conf_entry, self._s3_error, "Las contraseñas no coinciden.")
            return
            
        # Validación: mínimo 6 caracteres, 1 alfanumérico, 2 mayúsculas
        if len(pw) < 6:
            self._set_error(self._pw_entry, self._s3_error, "Debe tener al menos 6 caracteres.")
            return
        if not any(c.isalnum() for c in pw):
            self._set_error(self._pw_entry, self._s3_error, "Debe tener al menos 1 alfanumérico.")
            return
        if sum(1 for c in pw if c.isupper()) < 2:
            self._set_error(self._pw_entry, self._s3_error, "Debe tener al menos 2 mayúsculas.")
            return
            
        # Reset errors
        self._clear_error(self._pw_entry, self._s3_error)
        self._conf_entry.configure(border_color=COLORS["border"])
        
        # Save password
        if resetear_contrasena(self.dni_actual, pw):
            self._s3_success.configure(text="✅  Contraseña actualizada correctamente.")
            self._s3_btn.configure(text="Volver al Login  →", command=self._on_back)
            self._pw_entry.configure(state="disabled")
            self._conf_entry.configure(state="disabled")
        else:
            self._s3_error.configure(text="⚠  Hubo un error al actualizar la contraseña.")

    # ──────────────────────────────────────────────────────────
    # Utils
    # ──────────────────────────────────────────────────────────
    def _set_error(self, entry, label, msg):
        entry.configure(border_color=COLORS["error"], border_width=2)
        label.configure(text=f"⚠  {msg}")

    def _clear_error(self, entry, label):
        entry.configure(border_color=COLORS["border"], border_width=2)
        label.configure(text="")
