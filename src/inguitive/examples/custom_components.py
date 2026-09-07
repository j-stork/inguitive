"""
This file contains custom components for the inguitive application, including a base container, logo, title, and card components.
"""

from inguitive import Div, Header, Image

from .css import (
    BASE_CONTAINER_CSS,
    BRAND_COLORS,
    CARD_CONTENT_DIV_CSS,
    CARD_SHADOW_DIV_CSS,
    HEADER_CSS,
)


def BaseContainer(*content, width: str = "2xl") -> Div:  # noqa: N802
    """A base container component with a specified width.

    Args:
        *content: The content to be displayed inside the container.
        width: The width of the container. Defaults to "2xl".

    Returns:
        Div: The base container component.
    """
    base_css = BASE_CONTAINER_CSS
    if width:
        base_css += f" max-w-{width}"
    return Div(
        Div(
            *content,
            css=base_css,
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


def Title(text: str) -> Header:  # noqa: N802
    """A title component.

    Args:
        text: The text to be displayed as the title.

    Returns:
        Header: The title component.
    """
    return Header(text, css=HEADER_CSS)


def Card(*content) -> Div:  # noqa: N802
    """A simple card component with outer and inner divs."""
    return Div(
        Div(
            *content,
            css=CARD_CONTENT_DIV_CSS,
        ),
        css=CARD_SHADOW_DIV_CSS,
    )
