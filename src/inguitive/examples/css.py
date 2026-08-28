"""
CSS class constants for inguitive framework.

This module contains Tailwind CSS class string constants for common UI elements.
Users can extend this file with their own styling constants.
"""

# Colors
BRAND_COLORS = {
    "blue_400": "#3D6EF0",
    "blue_500": "#1147E8",
    "violet_600": "#CA00E0",
    "navy_500": "#4977C1",
    "navy_900": "#10182E",
    "navy_950": "#090E1B",
}

# Wrap the color values in square brackets for Tailwind CSS compatibility
for color_name, color_value in BRAND_COLORS.items():
    if "#" in color_value:
        BRAND_COLORS[color_name] = "[" + color_value.strip() + "]"


# CSS class for the top-level container
BASE_CONTAINER_CSS = f"flex flex-col justify-center align-center min-h-screen gap-6 p-6 bg-{BRAND_COLORS['navy_900']}"

# Common base styling for all buttons
BUTTON_BASE_CSS = "rounded-md px-3 py-2 font-semibold shadow-xs cursor-pointer"

# Primary button
BUTTON_PRIMARY_CSS = f"{BUTTON_BASE_CSS} bg-{BRAND_COLORS['blue_500']} text-white hover:bg-{BRAND_COLORS['blue_400']} active:bg-{BRAND_COLORS['blue_500']}"

# Secondary button
BUTTON_SECONDARY_CSS = f"{BUTTON_BASE_CSS} bg-gray-300 text-black hover:bg-gray-200 active:bg-gray-300"

# Card container styling
CARD_CONTAINER_CSS = "w-full max-w-md p-6 space-y-6 mx-auto bg-gray-100 rounded-xl shadow-md"

# Header text
HEADER_CSS = "font-bold text-3xl text-center text-white mb-12"

# Input and textarea fields
INPUT_CSS = "w-full p-2 border rounded-md"
