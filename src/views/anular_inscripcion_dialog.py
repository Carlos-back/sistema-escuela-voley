"""
Flamingo Sys — Gestión Integral Voley
views/anular_inscripcion_dialog.py — Diálogo de anulación de inscripción (HU02)
"""

import customtkinter as ctk

from theme import COLORS, FONTS, RADIUS, make_button, make_label
from services.inscripciones import MIN_CARACTERES_DETALLE, MOTIVOS_ANULACION, validar_motivo

PLACEHOLDER_MOTIVO = "Seleccioná un motivo"


class AnularInscripcionDialog(ctk.CTkToplevel):
    """
    Ventana modal para anular una inscripción vigente.

    El motivo es obligatorio y sale de una lista cerrada (así el informe los
    puede agrupar). Si es "Otro", hay que describirlo con 10+ caracteres.
    El botón "Anular inscripción" se habilita solo cuando el motivo es válido.

    on_confirmar(insc, motivo, detalle) -> str | None : retorna el error a
    mostrar, o None si la anulación salió bien (y el diálogo se cierra).
    """

    def __init__(self, master, inscripcion: dict, on_confirmar):
        super().__init__(master)
        self._insc = inscripcion
        self._on_confirmar = on_confirmar

        self.title("Anular inscripción")
        self.geometry("460x430")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["white"])
        self.transient(master)
        self._build_ui()
        self.after(50, self._hacer_modal)

    def _hacer_modal(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(self, height=4, fg_color=COLORS["error"], corner_radius=0
                     ).grid(row=0, column=0, sticky="ew")

        make_label(self, "🚫  Anular inscripción", variant="h3"
                   ).grid(row=1, column=0, sticky="w", padx=24, pady=(18, 4))
        insc = self._insc
        make_label(self, f"{insc['nombre']} {insc['apellido']} · {insc['nombre_grupo']} · "
                         f"Período {insc['periodo']}", variant="muted"
                   ).grid(row=2, column=0, sticky="w", padx=24)
        make_label(self, "La inscripción no se borra: queda anulada con su motivo\n"
                         "y se libera un lugar del cupo del grupo.",
                   variant="caption", justify="left"
                   ).grid(row=3, column=0, sticky="w", padx=24, pady=(6, 12))

        make_label(self, "Motivo *", variant="label"
                   ).grid(row=4, column=0, sticky="w", padx=24, pady=(0, 4))
        self._motivo_var = ctk.StringVar(value=PLACEHOLDER_MOTIVO)
        ctk.CTkOptionMenu(
            self, variable=self._motivo_var, values=list(MOTIVOS_ANULACION),
            font=FONTS.BASE(), height=40, corner_radius=RADIUS.MD,
            fg_color=COLORS["white"], button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"], text_color=COLORS["text_dark"],
            dropdown_fg_color=COLORS["white"], dropdown_text_color=COLORS["text_dark"],
            dropdown_hover_color=COLORS["primary_light"],
            command=lambda _v: self._validar(),
        ).grid(row=5, column=0, sticky="ew", padx=24)

        self._detalle_label = make_label(self, "Detalle", variant="label")
        self._detalle_label.grid(row=6, column=0, sticky="w", padx=24, pady=(12, 4))
        self._detalle = ctk.CTkTextbox(self, height=80, font=FONTS.BASE(),
                                       border_width=1, border_color=COLORS["border"],
                                       corner_radius=RADIUS.MD)
        self._detalle.grid(row=7, column=0, sticky="ew", padx=24)
        self._detalle.bind("<KeyRelease>", lambda e: self._validar())

        self._error = make_label(self, "", variant="error")
        self._error.grid(row=8, column=0, sticky="w", padx=24, pady=(6, 0))

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.grid(row=9, column=0, sticky="e", padx=24, pady=(10, 20))
        make_button(botones, text="Cancelar", variant="secondary",
                    command=self.destroy).pack(side="left", padx=(0, 10))
        self._confirmar_btn = make_button(botones, text="  Anular inscripción",
                                          variant="danger", command=self._confirmar)
        self._confirmar_btn.pack(side="left")
        self._validar()

    def _valores(self):
        motivo = self._motivo_var.get()
        detalle = self._detalle.get("1.0", "end").strip()
        return motivo, detalle

    def _validar(self) -> bool:
        motivo, detalle = self._valores()
        es_otro = motivo == "Otro"
        self._detalle_label.configure(
            text=f"Detalle * (mínimo {MIN_CARACTERES_DETALLE} caracteres)" if es_otro
            else "Detalle (opcional)")
        error = validar_motivo(motivo, detalle)
        # Solo se muestra el error del detalle cuando ya se eligió "Otro" y se escribió algo
        mostrar = error if (es_otro and detalle) else ""
        self._error.configure(text=f"⚠  {mostrar}" if mostrar else "")
        if error:
            self._confirmar_btn.configure(state="disabled", fg_color="#CCCCCC")
            return False
        self._confirmar_btn.configure(state="normal", fg_color=COLORS["error"])
        return True

    def _confirmar(self):
        if not self._validar():
            return
        motivo, detalle = self._valores()
        error = self._on_confirmar(self._insc, motivo, detalle)
        if error:
            self._error.configure(text=f"⚠  {error}")
            return
        self.grab_release()
        self.destroy()
