"""
#TODO: Add a description of this file and its purpose.
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
    # TODO: Add a docstring here.
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
    # TODO: Add a docstring here.
    return Div(
        Image(src="/static/inguitive_logo.svg", alt="inguitive logo", css="h-10 w-auto mt-0.5"),
        Image(src="/static/inguitive_text.svg", alt="inguitive text", css="h-10 w-auto"),
        css="flex justify-start w-full",
    )


def Title(text: str) -> Header:  # noqa: N802
    # TODO: Add a docstring here.
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
