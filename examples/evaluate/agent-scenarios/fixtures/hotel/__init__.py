"""Shared hotel booking components for ragbits evaluation examples.

This module provides reusable hotel booking tools and prompts that can be used
across different evaluation examples and agent scenarios.
"""

import importlib.util
from pathlib import Path

# Use importlib to import from the same directory (since we're inside a hyphenated directory)
_prompt_path = Path(__file__).parent / "prompt.py"
_prompt_spec = importlib.util.spec_from_file_location("prompt", _prompt_path)
_prompt_module = importlib.util.module_from_spec(_prompt_spec)
_prompt_spec.loader.exec_module(_prompt_module)
HotelPrompt = _prompt_module.HotelPrompt
HotelPromptInput = _prompt_module.HotelPromptInput

_tools_path = Path(__file__).parent / "tools.py"
_tools_spec = importlib.util.spec_from_file_location("tools", _tools_path)
_tools_module = importlib.util.module_from_spec(_tools_spec)
_tools_spec.loader.exec_module(_tools_module)
cancel_reservation = _tools_module.cancel_reservation
create_reservation = _tools_module.create_reservation
get_hotel_details = _tools_module.get_hotel_details
get_reservation = _tools_module.get_reservation
list_cities = _tools_module.list_cities
list_hotels = _tools_module.list_hotels
list_reservations = _tools_module.list_reservations
search_available_rooms = _tools_module.search_available_rooms

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
