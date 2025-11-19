"""Shared hotel booking components for ragbits evaluation examples.

This module provides reusable hotel booking tools and prompts that can be used
across different evaluation examples and agent scenarios.
"""

from examples.evaluate.fixtures.hotel.prompt import HotelPrompt, HotelPromptInput
from examples.evaluate.fixtures.hotel.tools import (
    cancel_reservation,
    create_reservation,
    get_hotel_details,
    get_reservation,
    list_cities,
    list_hotels,
    list_reservations,
    search_available_rooms,
)

__all__ = [
    "HotelPrompt",
    "HotelPromptInput",
    "cancel_reservation",
    "create_reservation",
    "get_hotel_details",
    "get_reservation",
    "list_cities",
    "list_hotels",
    "list_reservations",
    "search_available_rooms",
]
