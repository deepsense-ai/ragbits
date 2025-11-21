"""OAuth2 provider visual configuration (icons, colors, etc.)."""

from typing import Any


class OAuth2ProviderVisualConfig:
    """Visual configuration for OAuth2 providers (brand colors, icons, etc.)."""

    def __init__(
        self,
        name: str,
        display_name: str,
        color: str,
        button_color: str | None = None,
        text_color: str = "#FFFFFF",
        icon_svg: str | None = None,
    ):
        """
        Initialize provider visual configuration.

        Args:
            name: Provider identifier (e.g., 'google', 'discord')
            display_name: Human-readable provider name
            color: Brand color for the provider
            button_color: Optional button background color (defaults to color)
            text_color: Button text color (defaults to white)
            icon_svg: Optional SVG icon as string
        """
        self.name = name
        self.display_name = display_name
        self.color = color
        self.button_color = button_color or color
        self.text_color = text_color
        self.icon_svg = icon_svg

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "color": self.color,
            "button_color": self.button_color,
            "text_color": self.text_color,
            "icon_svg": self.icon_svg,
        }


# Provider visual configurations
PROVIDER_CONFIGS: dict[str, OAuth2ProviderVisualConfig] = {
    "google": OAuth2ProviderVisualConfig(
        name="google",
        display_name="Google",
        color="#4285F4",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>',  # noqa: E501
    ),
    "discord": OAuth2ProviderVisualConfig(
        name="discord",
        display_name="Discord",
        color="#5865F2",
        icon_svg='<svg width="20" height="20" viewBox="0 0 71 55" fill="none" xmlns="http://www.w3.org/2000/svg"><g clipPath="url(#clip0)"><path d="M60.1045 4.8978C55.5792 2.8214 50.7265 1.2916 45.6527 0.41542C45.5603 0.39851 45.468 0.440769 45.4204 0.525289C44.7963 1.6353 44.105 3.0834 43.6209 4.2216C38.1637 3.4046 32.7345 3.4046 27.3892 4.2216C26.905 3.0581 26.1886 1.6353 25.5617 0.525289C25.5141 0.443589 25.4218 0.40133 25.3294 0.41542C20.2584 1.2888 15.4057 2.8186 10.8776 4.8978C10.8384 4.9147 10.8048 4.9429 10.7825 4.9795C1.57795 18.7309 -0.943561 32.1443 0.293408 45.3914C0.299005 45.4562 0.335386 45.5182 0.385761 45.5576C6.45866 50.0174 12.3413 52.7249 18.1147 54.5195C18.2071 54.5477 18.305 54.5139 18.3638 54.4378C19.7295 52.5728 20.9469 50.6063 21.9907 48.5383C22.0523 48.4172 21.9935 48.2735 21.8676 48.2256C19.9366 47.4931 18.0979 46.6 16.3292 45.5858C16.1893 45.5041 16.1781 45.304 16.3068 45.2082C16.679 44.9293 17.0513 44.6391 17.4067 44.3461C17.471 44.2926 17.5606 44.2813 17.6362 44.3151C29.2558 49.6202 41.8354 49.6202 53.3179 44.3151C53.3935 44.2785 53.4831 44.2898 53.5502 44.3433C53.9057 44.6363 54.2779 44.9293 54.6529 45.2082C54.7816 45.304 54.7732 45.5041 54.6333 45.5858C52.8646 46.6197 51.0259 47.4931 49.0921 48.2228C48.9662 48.2707 48.9102 48.4172 48.9718 48.5383C50.038 50.6034 51.2554 52.5699 52.5959 54.435C52.6519 54.5139 52.7526 54.5477 52.845 54.5195C58.6464 52.7249 64.529 50.0174 70.6019 45.5576C70.6551 45.5182 70.6887 45.459 70.6943 45.3942C72.1747 30.0791 68.2147 16.7757 60.1968 4.9823C60.1772 4.9429 60.1437 4.9147 60.1045 4.8978ZM23.7259 37.3253C20.2276 37.3253 17.3451 34.1136 17.3451 30.1693C17.3451 26.225 20.1717 23.0133 23.7259 23.0133C27.308 23.0133 30.1626 26.2532 30.1066 30.1693C30.1066 34.1136 27.28 37.3253 23.7259 37.3253ZM47.3178 37.3253C43.8196 37.3253 40.9371 34.1136 40.9371 30.1693C40.9371 26.225 43.7636 23.0133 47.3178 23.0133C50.9 23.0133 53.7545 26.2532 53.6986 30.1693C53.6986 34.1136 50.9 37.3253 47.3178 37.3253Z" fill="currentColor"/></g><defs><clipPath id="clip0"><rect width="71" height="55" fill="white"/></clipPath></defs></svg>',  # noqa: E501
    ),
    "github": OAuth2ProviderVisualConfig(
        name="github",
        display_name="GitHub",
        color="#24292e",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path fillRule="evenodd" clipRule="evenodd" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" fill="currentColor"/></svg>',  # noqa: E501
    ),
    "microsoft": OAuth2ProviderVisualConfig(
        name="microsoft",
        display_name="Microsoft",
        color="#00A4EF",
        icon_svg='<svg width="20" height="20" viewBox="0 0 23 23" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h11v11H0V0z" fill="#F25022"/><path d="M12 0h11v11H12V0z" fill="#7FBA00"/><path d="M0 12h11v11H0V12z" fill="#00A4EF"/><path d="M12 12h11v11H12V12z" fill="#FFB900"/></svg>',  # noqa: E501
    ),
    "gitlab": OAuth2ProviderVisualConfig(
        name="gitlab",
        display_name="GitLab",
        color="#FC6D26",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M23.546 10.93L13.067.452c-.604-.603-1.582-.603-2.188 0L.395 10.93c-.526.529-.526 1.387 0 1.916l10.48 10.478c.604.604 1.582.604 2.188 0l10.48-10.478c.527-.529.527-1.387.003-1.916z" fill="#FC6D26"/><path d="M11.973 1.566L8.333 10.93h7.28l-3.64-9.364z" fill="#E24329"/><path d="M11.973 1.566L8.333 10.93H1.67l10.303-9.364z" fill="#FC6D26"/><path d="M1.67 10.93L.395 14.846c-.097.296.009.623.261.811l11.317 8.227-10.303-12.954z" fill="#FCA326"/><path d="M1.67 10.93h6.663L4.693 1.566c-.15-.458-.808-.458-.958 0L1.67 10.93z" fill="#E24329"/><path d="M22.277 10.93l1.274 3.916c.097.296-.009.623-.261.811l-11.317 8.227L22.277 10.93z" fill="#FCA326"/><path d="M22.277 10.93h-6.664l3.64-9.364c.15-.458.808-.458.958 0l2.066 9.364z" fill="#E24329"/><path d="M11.973 1.566l3.64 9.364h6.664L11.973 1.566z" fill="#FC6D26"/></svg>',  # noqa: E501
    ),
    "facebook": OAuth2ProviderVisualConfig(
        name="facebook",
        display_name="Facebook",
        color="#1877F2",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" fill="currentColor"/></svg>',  # noqa: E501
    ),
    "twitter": OAuth2ProviderVisualConfig(
        name="twitter",
        display_name="Twitter",
        color="#1DA1F2",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" fill="currentColor"/></svg>',  # noqa: E501
    ),
    "linkedin": OAuth2ProviderVisualConfig(
        name="linkedin",
        display_name="LinkedIn",
        color="#0A66C2",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" fill="currentColor"/></svg>',  # noqa: E501
    ),
    "apple": OAuth2ProviderVisualConfig(
        name="apple",
        display_name="Apple",
        color="#000000",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" fill="currentColor"/></svg>',  # noqa: E501
    ),
    "okta": OAuth2ProviderVisualConfig(
        name="okta",
        display_name="Okta",
        color="#007DC1",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="12" fill="#007DC1"/><circle cx="12" cy="12" r="6" fill="white"/></svg>',  # noqa: E501
    ),
}


def get_provider_visual_config(provider_name: str) -> OAuth2ProviderVisualConfig:
    """
    Get visual configuration for a provider.

    Args:
        provider_name: Provider identifier

    Returns:
        Visual configuration for the provider, or default config if not found
    """
    config = PROVIDER_CONFIGS.get(provider_name.lower())
    if config:
        return config

    # Return default configuration for unknown providers
    capitalized_name = provider_name.capitalize()
    return OAuth2ProviderVisualConfig(
        name=provider_name,
        display_name=capitalized_name,
        color="#6B7280",
        text_color="#FFFFFF",
        icon_svg='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" fill="currentColor"/></svg>',  # noqa: E501
    )
