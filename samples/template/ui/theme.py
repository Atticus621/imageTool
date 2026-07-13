"""Unified color, font, spacing, and radius constants for the ImageTool UI.

Import from here instead of hardcoding values. All widgets should reference
these constants to maintain visual consistency.
"""

# ── Background colors (4-level hierarchy) ────────────────────────────
BG_BASE = "#1a1b2e"          # Main background (splash, QGraphicsView)
BG_CANVAS = "#1e1f35"        # Node graph canvas (deep blue-purple)
BG_SURFACE = "#222338"       # Card/panel background
BG_INPUT = "#2a2b40"         # Input control background
BG_HOVER = "#32334a"         # Hover state
BG_SELECTED = "#3a3b55"      # Selected state

# ── Border colors ───────────────────────────────────────────────────
BORDER_DEFAULT = "#3a3b55"
BORDER_HOVER = "#4a4b65"     # Hover border color
BORDER_FOCUS = "#00b4d8"
BORDER_SUBTLE = "#2e2f45"

# ── Text colors ─────────────────────────────────────────────────────
TEXT_PRIMARY = "#e8e8f0"     # Primary text
TEXT_SECONDARY = "#9898b0"   # Secondary text
TEXT_MUTED = "#5a5a75"       # Placeholder / disabled text

# ── Accent colors ───────────────────────────────────────────────────
ACCENT = "#00b4d8"           # Primary accent
ACCENT_HOVER = "#00d4ff"
ACCENT_DIM = "#0088a8"

# ── Semantic colors ─────────────────────────────────────────────────
SUCCESS = "#34c759"
WARNING = "#ffb800"
DANGER = "#ff453a"

# ── Node state colors (softened) ────────────────────────────────────
NODE_IDLE = (88, 86, 105)        # Muted gray-purple
NODE_RUNNING = (200, 170, 40)    # Muted gold
NODE_SUCCESS = (50, 170, 80)     # Muted green
NODE_ERROR = (190, 60, 60)       # Muted red

# ── Port type colors (for ports and connection pipes) ────────────────
PORT_COLORS = {
    "image": "#4fc3f7",   # Light blue - image data
    "roi": "#ab47bc",     # Purple - ROI regions
    "number": "#66bb6a",  # Green - numeric values
    "string": "#ffa726",  # Orange - strings
    "boolean": "#ef5350", # Red - booleans
    "any": "#78909c",     # Gray-blue - generic
}

# ── Histogram channel colors ────────────────────────────────────────
HIST_BLUE = "#5b9bd5"
HIST_GREEN = "#6bc77a"
HIST_RED = "#e06060"

# ── Ruler colors ────────────────────────────────────────────────────
RULER_LINE = "#00c8ff"           # Measurement line color
RULER_PREVIEW = "#ffc800"        # Preview dashed line color
RULER_ENDPOINT = "#00c8ff"       # Endpoint dot color
RULER_LABEL_BG = "#000000"       # Label background (apply alpha in code)
RULER_LABEL_ALPHA = 200          # Label background transparency

# ── Range slider colors ────────────────────────────────────────────
SLIDER_TRACK = "#464650"
SLIDER_RANGE = "#0096c8"
SLIDER_HANDLE = "#00b4e6"
SLIDER_HANDLE_HOVER = "#3cd2ff"
SLIDER_HANDLE_DRAG = "#64e6ff"

# ── Border radius ───────────────────────────────────────────────────
RADIUS_SM = "3px"
RADIUS_MD = "4px"
RADIUS_LG = "6px"
RADIUS_XL = "8px"

# ── Spacing ─────────────────────────────────────────────────────────
SPACING_XS = 2
SPACING_SM = 4
SPACING_MD = 8
SPACING_LG = 12
SPACING_XL = 16

# ── Font ────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"   # Monospace for numeric displays
FONT_SIZE_XS = "9px"
FONT_SIZE_SM = "10px"
FONT_SIZE_MD = "11px"
FONT_SIZE_LG = "12px"
FONT_SIZE_XL = "14px"
FONT_SIZE_TITLE = "28px"        # Splash screen title
FONT_SIZE_SUBTITLE = "14px"     # Splash screen subtitle
FONT_SIZE_LOADING = "13px"      # Splash screen loading text
