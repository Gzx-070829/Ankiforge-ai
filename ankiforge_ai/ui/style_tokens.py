"""Central product visual constants shared by the PyQt workbench."""

APP_BG = "#211D1A"
SURFACE = "#29231F"
SURFACE_ELEVATED = "#332B26"
INPUT_BG = "#241F1C"
HOVER_BG = "#3A312B"
BORDER_SUBTLE = "#443931"
BORDER_STRONG = "#5A493E"
TEXT_PRIMARY = "#F5EEE8"
TEXT_SECONDARY = "#D8CCC2"
TEXT_MUTED = "#A8978A"
ACCENT = "#D98A55"
ACCENT_HOVER = "#E39A65"
ACCENT_SOFT = "rgba(217, 138, 85, 0.14)"
ACCENT_BORDER = "#80563A"
ACCENT_TEXT = "#EDB68C"
SUCCESS = "#7FAF86"
SUCCESS_BG = "#263229"
SUCCESS_BORDER = "#455E49"
SUCCESS_TEXT = "#AAD0B0"
WARNING = "#D6A35D"
WARNING_BG = "#372E22"
WARNING_BORDER = "#665039"
WARNING_TEXT = "#E8C58C"
DANGER = "#D77B72"
DANGER_BG = "#382523"
DANGER_BORDER = "#68413D"
DANGER_TEXT = "#E7A6A0"
DISABLED_BG = "#493426"
DISABLED_TEXT = "#A87C5D"
DISABLED_BORDER = "#664732"

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_XXL = 32

INPUT_HEIGHT = 40
BUTTON_HEIGHT = 36
PRIMARY_BUTTON_HEIGHT = 44
CHIP_HEIGHT = 28
COMPACT_QUEUE_ROW_HEIGHT = 32
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
        "accent_border": ACCENT_BORDER,
        "accent_text": ACCENT_TEXT,
        "success": SUCCESS,
        "success_bg": SUCCESS_BG,
        "success_border": SUCCESS_BORDER,
        "success_text": SUCCESS_TEXT,
        "warning": WARNING,
        "warning_bg": WARNING_BG,
        "warning_border": WARNING_BORDER,
        "warning_text": WARNING_TEXT,
        "danger": DANGER,
        "danger_bg": DANGER_BG,
        "danger_border": DANGER_BORDER,
        "danger_text": DANGER_TEXT,
        "disabled_bg": DISABLED_BG,
        "disabled_text": DISABLED_TEXT,
        "disabled_border": DISABLED_BORDER,
    }
