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
