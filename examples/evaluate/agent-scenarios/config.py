from pathlib import Path

from pydantic_settings import BaseSettings

from ragbits.evaluate.agent_simulation import DataSnapshot, DomainContext


class AppConfig(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # LLM configuration
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str
    # Observability configuration
    otel_exporter_endpoint: str = "http://localhost:4317"
    service_name: str = "ragbits-simple_agent"
    enable_tracing: bool = True
    enable_metrics: bool = True

    class Config:
        """Pydantic configuration for settings loading."""

        env_file = Path(__file__).parent.parent.parent / ".env"


config = AppConfig()

# Domain context helps the LLM checker understand hotel-specific concepts
domain_context = DomainContext(
    domain_type="hotel_booking",
    locale="pl_PL",
    metadata={
        "currency": "PLN",
        "cities": ["Kraków", "Warszawa", "Gdańsk"],
        "room_types": ["standard", "deluxe", "suite"],
        "available_tools": [
            "list_cities",
            "list_hotels",
            "get_hotel_details",
            "search_available_rooms",
            "create_reservation",
            "list_reservations",
            "get_reservation",
            "cancel_reservation",
        ],
    },
)

# Data snapshot grounds the simulated user with real hotel data
data_snapshot = DataSnapshot(
    description="Polish hotel booking system with hotels in Kraków, Warszawa, and Gdańsk",
    entities={
        "cities": ["Kraków", "Warszawa", "Gdańsk"],
        "sample_hotels": [
            "Grand Hotel Kraków (4.8 stars)",
            "Hotel Copernicus Kraków (4.9 stars)",
            "Sheraton Grand Warszawa (4.7 stars)",
            "Hotel Bristol Warszawa (4.9 stars)",
            "Hilton Gdańsk (4.7 stars)",
        ],
        "room_types": [
            "standard (250-380 PLN/night)",
            "deluxe (400-600 PLN/night)",
            "suite (600-900 PLN/night)",
        ],
        "date_range": "January 2025 - August 2025",
    },
)
