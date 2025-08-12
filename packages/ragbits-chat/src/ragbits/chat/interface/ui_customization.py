from pydantic import BaseModel, Field


class HeaderCustomization(BaseModel):
    """
    Customization for the header section of the UI.
    """

    title: str | None = Field(default=None, description="Custom title to be displayed instead of 'Ragbits Chat'")
    """Custom title to be displayed instead of 'Ragbits Chat'"""
    subtitle: str | None = Field(
        default=None, description="Custom subtitle to be displayed instead of 'by deepsense.ai'"
    )
    """Custom subtitle to be displayed instead of 'by deepsense.ai'"""
    logo: str | None = Field(
        default=None,
        description="Custom logo URL or content. The logo can also be served from 'static' directory inside 'ui-buid'",
    )
    """Custom logo URL or content. The logo can also be served from 'static' directory inside 'ui-buid"""


class PageMetaCustomization(BaseModel):
    """
    Customization for the meta properites of the UI
    """

    favicon: str | None = Field(
        default=None,
        description=(
            "Custom favicon URL or content. If `None` logo is used."
            "The favicon can also be serverd from 'static' directory inside 'ui-build'"
        ),
    )
    (
        "Custom favicon URL or content. If `None` logo is used."
        "The favicon can also be serverd from 'static' directory inside 'ui-build'"
    )
    page_title: str | None = Field(
        default=None,
        description="Custom title for the page displayed in the browser's bar. If `None` header title is used.",
    )
    "Custom title for the page displayed in the browser's bar. If `None` header title is used."


class UICustomization(BaseModel):
    """
    Customization for the UI.
    """

    header: HeaderCustomization | None = Field(default=None, description="Custom header configuration")
    """Custom header configuration"""
    welcome_message: str | None = Field(
        default=None, description="Custom welcome message to be displayed on the UI. It supports Markdown."
    )
    """Custom welcome message to be displayed on the UI. It supports Markdown."""
    meta: PageMetaCustomization | None = Field(default=None, description="Custom meta properties customization")
