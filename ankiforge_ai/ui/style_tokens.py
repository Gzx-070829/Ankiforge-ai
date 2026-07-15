"""Central product visual constants shared by the PyQt workbench."""

APP_BG = "#0D1117"
SURFACE = "#111827"
SURFACE_ELEVATED = "#161B22"
INPUT_BG = "#0F141B"
HOVER_BG = "#1C2430"
BORDER_SUBTLE = "#263241"
BORDER_STRONG = "#334155"
TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#CBD5E1"
TEXT_MUTED = "#7D8EA3"
ACCENT = "#7C5CFF"
ACCENT_HOVER = "#8B73FF"
ACCENT_SOFT = "rgba(124, 92, 255, 0.12)"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
DANGER = "#EF4444"

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_XXL = 32

INPUT_HEIGHT = 40
BUTTON_HEIGHT = 36
PRIMARY_BUTTON_HEIGHT = 44
CONTROL_RADIUS = 10
PANEL_RADIUS = 12
SECTION_PADDING = 18
FORM_ROW_GAP = 12
FORM_LABEL_WIDTH = 96


def product_palette() -> dict[str, str]:
    """Return a copy so callers cannot mutate module-level tokens."""

    return {
        "app_bg": APP_BG,
        "surface": SURFACE,
        "surface_elevated": SURFACE_ELEVATED,
        "input_bg": INPUT_BG,
        "hover_bg": HOVER_BG,
        "border_subtle": BORDER_SUBTLE,
        "border_strong": BORDER_STRONG,
        "text_primary": TEXT_PRIMARY,
        "text_secondary": TEXT_SECONDARY,
        "text_muted": TEXT_MUTED,
        "accent": ACCENT,
        "accent_hover": ACCENT_HOVER,
        "accent_soft": ACCENT_SOFT,
        "success": SUCCESS,
        "warning": WARNING,
        "danger": DANGER,
    }
