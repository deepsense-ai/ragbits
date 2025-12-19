"""Hotel API tools for ragbits agents.

These tools provide access to hotel booking functionality via direct service calls.
The tools use an in-memory SQLite database populated from the hotel configuration.
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import HotelService

# Context variable for thread/async-safe service instance
_service_var: ContextVar[HotelService | None] = ContextVar("hotel_service", default=None)


def _get_service() -> HotelService:
    """Get the current service instance from context."""
    service = _service_var.get()
    if service is None:
        raise RuntimeError("HotelService not initialized. Tools must be used with HotelChat.")
    return service


def set_service(service: HotelService) -> None:
    """Set the service instance in context. Called by HotelChat during initialization."""
    _service_var.set(service)


# =============================================================================
# Hotel API Tools
# =============================================================================


async def list_cities() -> str:
    """
    Get a list of all available cities with hotels.

    Returns:
        str: JSON string containing list of city names
    """
    try:
        service = _get_service()
        cities = service.list_cities()
        return json.dumps(cities, indent=2)
    except Exception as e:
        return f"Error fetching cities: {e}"


async def list_hotels(city: str | None = None) -> str:
    """
    Get a list of hotels, optionally filtered by city.

    Args:
        city: Optional city name to filter hotels (e.g., "Kraków", "Warszawa", "Gdańsk")

    Returns:
        str: JSON string containing list of hotels with id, name, city, address, rating, and amenities
    """
    try:
        service = _get_service()
        hotels = service.list_hotels(city=city)
        return json.dumps([h.model_dump() for h in hotels], indent=2)
    except Exception as e:
        return f"Error fetching hotels: {e}"


async def get_hotel_details(hotel_id: int) -> str:
    """
    Get detailed information about a specific hotel including all its rooms.

    Args:
        hotel_id: The ID of the hotel to retrieve

    Returns:
        str: JSON string containing hotel details with rooms, including room id,
            number, type, price, capacity, and amenities
    """
    try:
        service = _get_service()
        hotel = service.get_hotel_detail(hotel_id)
        return json.dumps(hotel.model_dump(), indent=2)
    except LookupError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error fetching hotel details: {e}"


async def search_available_rooms(
    start_date: str,
    end_date: str,
    city: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    room_type: str | None = None,
) -> str:
    """
    Search for available rooms matching the specified criteria.

    Args:
        start_date: Check-in date in YYYY-MM-DD format (e.g., "2025-03-01")
        end_date: Check-out date in YYYY-MM-DD format (e.g., "2025-03-05")
        city: Optional city name to filter by (e.g., "Kraków", "Warszawa", "Gdańsk")
        min_price: Optional minimum price per night in PLN
        max_price: Optional maximum price per night in PLN
        room_type: Optional room type filter ("standard", "deluxe", or "suite")

    Returns:
        str: JSON string containing list of available rooms with hotel and room details
    """
    try:
        service = _get_service()
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        rooms = service.find_available_rooms(
            start_date=start,
            end_date=end,
            city=city,
            min_price=min_price,
            max_price=max_price,
            room_type=room_type,
        )
        return json.dumps([r.model_dump() for r in rooms], indent=2, default=str)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error searching rooms: {e}"


async def create_reservation(
    hotel_id: int,
    room_id: int,
    guest_name: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Create a new hotel reservation.

    Args:
        hotel_id: The ID of the hotel
        room_id: The ID of the room to reserve
        guest_name: Name of the guest making the reservation
        start_date: Check-in date in YYYY-MM-DD format (e.g., "2025-03-10")
        end_date: Check-out date in YYYY-MM-DD format (e.g., "2025-03-12")

    Returns:
        str: JSON string containing reservation details including reservation_id,
            hotel_name, room details, and total_price
    """
    try:
        service = _get_service()
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        reservation = service.create_reservation(
            hotel_id=hotel_id,
            room_id=room_id,
            guest_name=guest_name,
            start_date=start,
            end_date=end,
        )
        return json.dumps(reservation.model_dump(), indent=2, default=str)
    except (ValueError, LookupError) as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error creating reservation: {e}"


async def list_reservations(guest_name: str | None = None) -> str:
    """
    Get a list of reservations, optionally filtered by guest name.

    Args:
        guest_name: Optional guest name to filter reservations (partial match supported)

    Returns:
        str: JSON string containing list of reservations with details
    """
    try:
        service = _get_service()
        reservations = service.list_reservations(guest_name=guest_name)
        return json.dumps([r.model_dump() for r in reservations], indent=2, default=str)
    except Exception as e:
        return f"Error fetching reservations: {e}"


async def get_reservation(reservation_id: int) -> str:
    """
    Get details of a specific reservation.

    Args:
        reservation_id: The ID of the reservation to retrieve

    Returns:
        str: JSON string containing reservation details including hotel, room, guest, dates, and total price
    """
    try:
        service = _get_service()
        reservation = service.get_reservation(reservation_id)
        return json.dumps(reservation.model_dump(), indent=2, default=str)
    except LookupError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error fetching reservation: {e}"


async def cancel_reservation(reservation_id: int) -> str:
    """
    Cancel an existing reservation and free up the room.

    Args:
        reservation_id: The ID of the reservation to cancel

    Returns:
        str: Success message confirming the cancellation
    """
    try:
        service = _get_service()
        message = service.cancel_reservation(reservation_id)
        return json.dumps({"detail": message}, indent=2)
    except LookupError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error canceling reservation: {e}"
