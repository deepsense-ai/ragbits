"""Shared hotel booking components for ragbits evaluation examples.

This module provides reusable hotel booking tools and prompts that can be used
across different evaluation examples and agent scenarios.

The hotel booking functionality uses an in-memory SQLite database populated
from a JSON configuration file. No external HTTP API server is required.
"""

from . import prompt, tools
from .hotel_chat import HotelChat
from .service import HotelService

# Re-export prompt classes
HotelPrompt = prompt.HotelPrompt
HotelPromptInput = prompt.HotelPromptInput

# Re-export tools
cancel_reservation = tools.cancel_reservation
create_reservation = tools.create_reservation
get_hotel_details = tools.get_hotel_details
get_reservation = tools.get_reservation
list_cities = tools.list_cities
list_hotels = tools.list_hotels
list_reservations = tools.list_reservations
search_available_rooms = tools.search_available_rooms


__all__ = [
    "HotelChat",
    "HotelPrompt",
    "HotelPromptInput",
    "HotelService",
    "cancel_reservation",
    "create_reservation",
    "get_hotel_details",
    "get_reservation",
    "list_cities",
    "list_hotels",
    "list_reservations",
    "search_available_rooms",
]
