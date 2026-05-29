"""
CSS class constants for INGUITIVE framework.

This module contains Tailwind CSS class string constants for common UI elements.
Users can extend this file with their own styling constants.
"""

# --- Styling constants ---
# Common base styling for all buttons
BUTTON_BASE_CSS = "rounded-md p-2 text-sm font-semibold shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-600 cursor-pointer"

# Primary button (indigo theme)
BUTTON_PRIMARY_CSS = f"{BUTTON_BASE_CSS} bg-slate-600 text-white active:bg-slate-700"

# Secondary button (white theme with gray ring)
BUTTON_SECONDARY_CSS = f"{BUTTON_BASE_CSS} bg-slate-300 text-black active:bg-slate-400"
