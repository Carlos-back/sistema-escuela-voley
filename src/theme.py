"""
Flamingo Sys — Gestión Integral Voley
theme.py — Sistema de diseño centralizado

Funciona como un "CSS" para CustomTkinter:
  - COLORS    → variables CSS (:root { --primary: ... })
  - FONTS     → tipografías globales
  - Factories → funciones que crean widgets pre-estilizados
                (equivalente a clases CSS o styled-components)

Uso:
    from theme import COLORS, make_button, make_entry, make_label

    btn = make_button(parent, text="Guardar", variant="primary")
    inp = make_entry(parent, placeholder="Tu nombre")
"""

import customtkinter as ctk

# ══════════════════════════════════════════════════════════════════
# PALETA DE COLORES — equivalente a :root { --variable: value }
# ══════════════════════════════════════════════════════════════════

COLORS = {
    # Marca
    "primary":           "#E91E8C",
    "primary_hover":     "#C4177A",
    "primary_light":     "#FDF2F8",

    # Superficie
    "bg":                "#F5F5F5",
    "white":             "#FFFFFF",
    "card_bg":           "#FFFFFF",

    # Sidebar
    "sidebar_bg":        "#2B2B2B",
    "sidebar_text":      "#CCCCCC",
    "sidebar_active":    "#E91E8C",
    "sidebar_hover":     "#3D3D3D",

    # Texto
    "text_dark":         "#1A1A2E",
    "text_muted":        "#6B7280",

    # Bordes
    "border":            "#E2E8F0",

    # Semánticos
    "error":             "#E53E3E",
    "error_light":       "#FEF2F2",
    "success":           "#38A169",
    "success_light":     "#ECFDF5",
    "warning":           "#F59E0B",
    "warning_light":     "#FEF3C7",
    "info":              "#6366F1",
    "info_light":        "#EEF2FF",
}


# ══════════════════════════════════════════════════════════════════
# TIPOGRAFÍAS — lazy factories para evitar "Too early to use font"
#
# CTkFont necesita que la ventana Tk ya exista cuando se crea.
# Por eso usamos funciones en vez de atributos de clase.
#
# Uso:    font = FONTS.BASE()      en vez de    FONTS.BASE()
# ══════════════════════════════════════════════════════════════════

class _FontFactory:
    """
    Equivalente a las variables de tipografía de un design system CSS:
        --font-body: 13px;
        --font-heading: 24px bold;

    Cada método devuelve una nueva CTkFont cuando se llama.
    Se usa lru_cache por tamaño+peso para no crear fuentes repetidas.
    """

    @staticmethod
    def _f(size: int, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(size=size, weight=weight)

    def XS(self):         return self._f(10)
    def SM(self):         return self._f(11)
    def BASE(self):       return self._f(13)
    def MD(self):         return self._f(14)
    def LG(self):         return self._f(16)
    def XL(self):         return self._f(20)
    def XXL(self):        return self._f(24)
    def XXXL(self):       return self._f(32)

    def SM_BOLD(self):    return self._f(11, "bold")
    def BASE_BOLD(self):  return self._f(13, "bold")
    def MD_BOLD(self):    return self._f(14, "bold")
    def LG_BOLD(self):    return self._f(16, "bold")
    def XL_BOLD(self):    return self._f(20, "bold")
    def XXL_BOLD(self):   return self._f(24, "bold")
    def XXXL_BOLD(self):  return self._f(32, "bold")

    # Roles semánticos
    def HEADING_1(self):  return self._f(28, "bold")
    def HEADING_2(self):  return self._f(22, "bold")
    def HEADING_3(self):  return self._f(18, "bold")
    def BODY(self):       return self._f(13)
    def BODY_BOLD(self):  return self._f(13, "bold")
    def CAPTION(self):    return self._f(11)
    def LABEL(self):      return self._f(12, "bold")
    def OVERLINE(self):   return self._f(10, "bold")


# Instancia global — se usa como FONTS.BASE() en todo el proyecto
FONTS = _FontFactory()


# ══════════════════════════════════════════════════════════════════
# DIMENSIONES — equivalente a spacing / sizing tokens en CSS
# ══════════════════════════════════════════════════════════════════

class SPACING:
    XS  = 4
    SM  = 8
    MD  = 12
    LG  = 16
    XL  = 24
    XXL = 32

class RADIUS:
    SM  = 6
    MD  = 10
    LG  = 14
    XL  = 20
    FULL = 999   # pill / circle


# ══════════════════════════════════════════════════════════════════
# FACTORIES DE WIDGETS — equivalente a clases CSS / styled-components
#
# Cada función devuelve un widget pre-estilizado.
# Solo necesitás pasarle el padre y los parámetros que cambian.
# ══════════════════════════════════════════════════════════════════

# ── Botones ───────────────────────────────────────────────────────

def make_button(parent, text: str, variant: str = "primary",
                size: str = "md", **kwargs) -> ctk.CTkButton:
    """
    Crea un botón pre-estilizado.

    variant: "primary" | "secondary" | "ghost" | "danger" | "success"
    size:    "sm" | "md" | "lg"
    """
    variants = {
        "primary":   {"fg_color": COLORS["primary"],   "hover_color": COLORS["primary_hover"], "text_color": "#FFFFFF", "border_width": 0},
        "secondary": {"fg_color": COLORS["white"],     "hover_color": "#F3F4F6",              "text_color": COLORS["text_dark"],  "border_width": 1, "border_color": COLORS["border"]},
        "ghost":     {"fg_color": "transparent",       "hover_color": COLORS["bg"],            "text_color": COLORS["primary"],    "border_width": 0},
        "danger":    {"fg_color": COLORS["error"],     "hover_color": "#C53030",              "text_color": "#FFFFFF", "border_width": 0},
        "success":   {"fg_color": COLORS["success"],   "hover_color": "#2F855A",              "text_color": "#FFFFFF", "border_width": 0},
        "warning":   {"fg_color": COLORS["warning"],   "hover_color": "#D97706",              "text_color": "#FFFFFF", "border_width": 0},
        "info":      {"fg_color": COLORS["info"],      "hover_color": "#4F46E5",              "text_color": "#FFFFFF", "border_width": 0},
    }

    sizes = {
        "sm": {"height": 32, "font": FONTS.SM_BOLD(),   "corner_radius": RADIUS.SM, "padx": 12},
        "md": {"height": 40, "font": FONTS.BASE_BOLD(), "corner_radius": RADIUS.MD, "padx": 16},
        "lg": {"height": 48, "font": FONTS.MD_BOLD(),   "corner_radius": RADIUS.LG, "padx": 20},
    }

    style = {**variants.get(variant, variants["primary"]), **sizes.get(size, sizes["md"])}
    style.pop("padx", None)
    style.update(kwargs)

    return ctk.CTkButton(parent, text=text, **style)


# ── Entradas de texto ─────────────────────────────────────────────

def make_entry(parent, placeholder: str = "", variant: str = "default",
               **kwargs) -> ctk.CTkEntry:
    """
    Crea un CTkEntry pre-estilizado.

    variant: "default" | "error" | "success" | "disabled"
    """
    variants = {
        "default":  {"border_color": COLORS["border"],   "fg_color": COLORS["white"],   "text_color": COLORS["text_dark"]},
        "error":    {"border_color": COLORS["error"],    "fg_color": COLORS["error_light"], "text_color": COLORS["text_dark"]},
        "success":  {"border_color": COLORS["success"],  "fg_color": COLORS["success_light"], "text_color": COLORS["text_dark"]},
        "disabled": {"border_color": COLORS["border"],   "fg_color": "#F3F4F6",         "text_color": COLORS["text_muted"], "state": "disabled"},
    }

    style = variants.get(variant, variants["default"]).copy()
    style.update(kwargs)

    return ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        font=FONTS.BASE(),
        height=42,
        corner_radius=RADIUS.MD,
        **style
    )


# ── Labels / Textos ───────────────────────────────────────────────

def make_label(parent, text: str, variant: str = "body", **kwargs) -> ctk.CTkLabel:
    """
    Crea un CTkLabel pre-estilizado según su rol semántico.

    variant: "h1" | "h2" | "h3" | "body" | "caption" | "muted" | "error" | "success" | "overline"
    """
    variants = {
        "h1":       {"font": FONTS.HEADING_1(), "text_color": COLORS["text_dark"]},
        "h2":       {"font": FONTS.HEADING_2(), "text_color": COLORS["text_dark"]},
        "h3":       {"font": FONTS.HEADING_3(), "text_color": COLORS["text_dark"]},
        "body":     {"font": FONTS.BODY(),      "text_color": COLORS["text_dark"]},
        "bold":     {"font": FONTS.BODY_BOLD(), "text_color": COLORS["text_dark"]},
        "caption":  {"font": FONTS.CAPTION(),   "text_color": COLORS["text_muted"]},
        "muted":    {"font": FONTS.BASE(),      "text_color": COLORS["text_muted"]},
        "label":    {"font": FONTS.LABEL(),     "text_color": COLORS["text_dark"]},
        "overline": {"font": FONTS.OVERLINE(),  "text_color": COLORS["text_muted"]},
        "error":    {"font": FONTS.SM(),        "text_color": COLORS["error"]},
        "success":  {"font": FONTS.SM(),        "text_color": COLORS["success"]},
        "primary":  {"font": FONTS.BASE_BOLD(), "text_color": COLORS["primary"]},
    }

    style = variants.get(variant, variants["body"]).copy()
    style.update(kwargs)
    return ctk.CTkLabel(parent, text=text, **style)


# ── Cards / Contenedores ──────────────────────────────────────────

def make_card(parent, variant: str = "default", **kwargs) -> ctk.CTkFrame:
    """
    Crea un frame estilizado como "card".

    variant: "default" | "flat" | "accent" | "error" | "success"
    """
    variants = {
        "default": {"fg_color": COLORS["white"],         "border_color": COLORS["border"],   "border_width": 1},
        "flat":    {"fg_color": COLORS["bg"],             "border_width": 0},
        "accent":  {"fg_color": COLORS["primary_light"],  "border_color": COLORS["primary"],  "border_width": 1},
        "error":   {"fg_color": COLORS["error_light"],    "border_color": COLORS["error"],    "border_width": 1},
        "success": {"fg_color": COLORS["success_light"],  "border_color": COLORS["success"],  "border_width": 1},
        "warning": {"fg_color": COLORS["warning_light"],  "border_color": COLORS["warning"],  "border_width": 1},
    }

    style = variants.get(variant, variants["default"]).copy()
    style.update(kwargs)
    return ctk.CTkFrame(parent, corner_radius=RADIUS.LG, **style)


# ── Separadores ───────────────────────────────────────────────────

def make_divider(parent, orientation: str = "horizontal",
                 color: str = None, **kwargs) -> ctk.CTkFrame:
    """
    Línea separadora.

    Comparación CSS:
        hr { border: 1px solid #E2E8F0; }
    """
    clr = color or COLORS["border"]
    if orientation == "horizontal":
        return ctk.CTkFrame(parent, height=1, fg_color=clr,
                            corner_radius=0, **kwargs)
    else:
        return ctk.CTkFrame(parent, width=1, fg_color=clr,
                            corner_radius=0, **kwargs)


# ── Badge / Chip ──────────────────────────────────────────────────

def make_badge(parent, text: str, variant: str = "primary") -> ctk.CTkLabel:
    """
    Etiqueta pequeña de estado (como un chip/tag en CSS).

    variant: "primary" | "success" | "warning" | "error" | "info" | "neutral"

    Comparación CSS:
        .badge { padding: 2px 10px; border-radius: 999px; font-size: 11px; }
        .badge-success { background: #ECFDF5; color: #38A169; }
    """
    variants = {
        "primary": (COLORS["primary_light"], COLORS["primary"]),
        "success": (COLORS["success_light"], COLORS["success"]),
        "warning": (COLORS["warning_light"], COLORS["warning"]),
        "error":   (COLORS["error_light"],   COLORS["error"]),
        "info":    (COLORS["info_light"],    COLORS["info"]),
        "neutral": ("#F3F4F6",               COLORS["text_muted"]),
    }
    bg, fg = variants.get(variant, variants["neutral"])
    return ctk.CTkLabel(
        parent,
        text=f"  {text}  ",
        font=FONTS.SM_BOLD(),
        fg_color=bg,
        text_color=fg,
        corner_radius=RADIUS.FULL,
    )


# ── Accent bar (barra de color superior de sección) ───────────────

def make_accent_bar(parent) -> ctk.CTkFrame:
    """Barra fucsia de 4px en la parte superior de un panel."""
    return ctk.CTkFrame(parent, height=4, fg_color=COLORS["primary"],
                        corner_radius=0)
