"""
CSS class constants for inguitive framework.

This module contains Tailwind CSS class string constants for common UI elements.
Users can extend this file with their own styling constants.
"""

# Colors
BRAND_COLORS = {
    "blue": "#155dff",
    "blue_light": "#3c7dff",
    "green": "#00df72",
    "green_light": "#40fa8c",
    "yellow": "#ffba00",
    "yellow_light": "#ffd96e",
    "red": "#ff6367",
    "red_light": "#ff8c8b",
    "background_0": "#0b1628",
    "background_1": "#273347",
    "background_2": "#465369",
    "text_0": "#c2ccd8",
    "text_1": "#dce6f2",
    "text_2": "#ffffff"
}


# Wrap the color values in square brackets for Tailwind CSS compatibility
for color_name, color_value in BRAND_COLORS.items():
    if "#" in color_value:
        BRAND_COLORS[color_name] = "[" + color_value.strip() + "]"


# CSS class for the top-level container
BASE_CONTAINER_CSS = f"flex flex-col justify-center items-center w-full min-h-screen gap-9 p-6 mx-auto bg-{BRAND_COLORS['background_0']}"

# Common base styling for all buttons
BASE_BUTTON_CSS = "px-3 py-2 font-semibold border-2 border-black cursor-pointer text-black/80"

# Primary buttons
BUTTON_PRIMARY_BLUE_CSS = f"{BASE_BUTTON_CSS} bg-{BRAND_COLORS['blue']} hover:bg-{BRAND_COLORS['blue_light']} active:bg-{BRAND_COLORS['blue']}"
BUTTON_PRIMARY_GREEN_CSS = f"{BASE_BUTTON_CSS} bg-{BRAND_COLORS['green']} hover:bg-{BRAND_COLORS['green_light']} active:bg-{BRAND_COLORS['green']}"
BUTTON_PRIMARY_YELLOW_CSS = f"{BASE_BUTTON_CSS} bg-{BRAND_COLORS['yellow']} hover:bg-{BRAND_COLORS['yellow_light']} active:bg-{BRAND_COLORS['yellow']}"
BUTTON_PRIMARY_RED_CSS = f"{BASE_BUTTON_CSS} bg-{BRAND_COLORS['red']} hover:bg-{BRAND_COLORS['red_light']} active:bg-{BRAND_COLORS['red']}"

# Secondary button
BUTTON_SECONDARY_CSS = f"{BASE_BUTTON_CSS} bg-{BRAND_COLORS['text_0']} hover:bg-{BRAND_COLORS['text_1']} active:bg-{BRAND_COLORS['text_0']}"

# Card container styling
CARD_SHADOW_DIV_CSS = "w-full translate-2 bg-black"
CARD_CONTENT_DIV_CSS = f"w-full p-6 space-y-6 border-2 border-black bg-{BRAND_COLORS['background_1']} -translate-2"

# Header text
BASE_HEADER_CSS = f"font-bold text-{BRAND_COLORS['text_2']}"

# Standard text
TEXT_CSS = f"text-{BRAND_COLORS['text_0']}"

# Helper text
HELP_TEXT_CSS = f"text-sm mt-1 text-{BRAND_COLORS['text_0']}"

# Label text
LABEL_CSS = f"font-medium text-{BRAND_COLORS['text_1']}"

# Input and textarea fields
INPUT_CSS = f"w-full p-2 border-2 border-black rounded-none bg-{BRAND_COLORS['background_2']} text-{BRAND_COLORS['text_0']} placeholder:text-{BRAND_COLORS['text_0']}"

# Link styling
LINK_CSS = f"font-semibold text-{BRAND_COLORS['blue']} underline hover:text-{BRAND_COLORS['blue_light']} active:text-{BRAND_COLORS['blue']}"
