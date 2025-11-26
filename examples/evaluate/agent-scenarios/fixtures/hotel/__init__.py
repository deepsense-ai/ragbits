"""Shared hotel booking components for ragbits evaluation examples.

This module provides reusable hotel booking tools and prompts that can be used
across different evaluation examples and agent scenarios.
"""

from . import prompt, tools
from .hotel_chat import HotelChat

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
    "cancel_reservation",
    "create_reservation",
    "get_hotel_details",
    "get_reservation",
    "list_cities",
    "list_hotels",
    "list_reservations",
    "search_available_rooms",
]
