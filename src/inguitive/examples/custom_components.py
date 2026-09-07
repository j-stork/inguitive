"""
This file contains custom components for the inguitive application, including a base container, logo, title, and card components.
"""

from inguitive import Div, Header, Image

from .css import (
    BASE_CONTAINER_CSS,
    BASE_HEADER_CSS,
    BRAND_COLORS,
    CARD_CONTENT_DIV_CSS,
    CARD_SHADOW_DIV_CSS,
)


def BaseContainer(*content, width: str = "2xl") -> Div:  # noqa: N802
    """A base container component with a specified width.

    Args:
        *content: The content to be displayed inside the container.
        width: The width of the container. Defaults to "2xl".

    Returns:
        Div: The base container component.
    """
    css = BASE_CONTAINER_CSS
    if width:
        css += f" max-w-{width}"
    return Div(
        Div(
            *content,
            css=css,
        ),
        css=f"bg-{BRAND_COLORS['background_0']}",
    )


def InguitiveLogo() -> Div:  # noqa: N802
    """A component displaying the inguitive logo.

    Returns:
        Div: The logo component.
    """
    return Div(
        Image(src="/static/inguitive_logo.svg", alt="inguitive logo", css="h-10 w-auto mt-0.5"),
        Image(src="/static/inguitive_text.svg", alt="inguitive text", css="h-10 w-auto"),
        css="flex justify-start w-full",
    )


def Title(text: str, level: int = 1) -> Header:  # noqa: N802
    """A title component.

    Args:
        text: The text to be displayed as the title.
        level: The heading level (1-6). Defaults to 1.

    Returns:
        Header: The title component.
    """
    css = BASE_HEADER_CSS
    if level == 1:
        css += " text-4xl"
    elif level == 2:
        css += " text-2xl"
    elif level == 3:
        css += " text-xl"
    return Header(text, level=level, css=css)


def Card(*content) -> Div:  # noqa: N802
    """A simple card component with outer and inner divs."""
    return Div(
        Div(
            *content,
            css=CARD_CONTENT_DIV_CSS,
        ),
        css=CARD_SHADOW_DIV_CSS,
    )
