"""Hotel API tools for ragbits agents.

These tools provide access to hotel booking functionality via HTTP API calls.
The tools are designed to work with the hotel_api FastAPI service.
"""

import json

import httpx

# =============================================================================
# Hotel API Tools
# =============================================================================

HOTEL_API_BASE_URL = "http://localhost:8000"


async def list_cities(process_id: int | str | None = None) -> str:
    """
    Get a list of all available cities with hotels.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).

    Returns:
        str: JSON string containing list of city names
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HOTEL_API_BASE_URL}/{process_id}_cities")
            response.raise_for_status()
            cities = response.json()
            return json.dumps(cities, indent=2)
    except httpx.RequestError as e:
        return f"Error fetching cities: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing cities: {e}"


async def list_hotels(process_id: int | str | None = None, city: str | None = None) -> str:
    """
    Get a list of hotels, optionally filtered by city.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
        city: Optional city name to filter hotels (e.g., "Kraków", "Warszawa", "Gdańsk")

    Returns:
        str: JSON string containing list of hotels with id, name, city, address, rating, and amenities
    """
    try:
        params = {}
        if city:
            params["city"] = city

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HOTEL_API_BASE_URL}/{process_id}_hotels", params=params)
            response.raise_for_status()
            hotels = response.json()
            return json.dumps(hotels, indent=2)
    except httpx.RequestError as e:
        return f"Error fetching hotels: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing hotels: {e}"


async def get_hotel_details(process_id: int | str | None = None, hotel_id: int | None = None) -> str:
    """
    Get detailed information about a specific hotel including all its rooms.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
        hotel_id: The ID of the hotel to retrieve

    Returns:
        str: JSON string containing hotel details with rooms, including room id,
            number, type, price, capacity, and amenities
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HOTEL_API_BASE_URL}/{process_id}_hotels/{hotel_id}")
            response.raise_for_status()
            hotel = response.json()
            return json.dumps(hotel, indent=2)
    except httpx.RequestError as e:
        return f"Error fetching hotel details: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing hotel details: {e}"


async def search_available_rooms(
    process_id: int | str | None = None,
    start_date: str = None,
    end_date: str = None,
    city: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    room_type: str | None = None,
) -> str:
    """
    Search for available rooms matching the specified criteria.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
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
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }
        if city:
            params["city"] = city
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if room_type:
            params["room_type"] = room_type

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HOTEL_API_BASE_URL}/{process_id}_rooms/available", params=params)
            response.raise_for_status()
            rooms = response.json()
            return json.dumps(rooms, indent=2)
    except httpx.RequestError as e:
        return f"Error searching rooms: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing room search: {e}"


async def create_reservation(
    process_id: int | str | None = None,
    hotel_id: int = None,
    room_id: int = None,
    guest_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Create a new hotel reservation.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
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
        payload = {
            "hotel_id": hotel_id,
            "room_id": room_id,
            "guest_name": guest_name,
            "start_date": start_date,
            "end_date": end_date,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{HOTEL_API_BASE_URL}/{process_id}_reservations",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            reservation = response.json()
            return json.dumps(reservation, indent=2)
    except httpx.RequestError as e:
        return f"Error creating reservation: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing reservation: {e}"


async def list_reservations(process_id: int | str | None = None, guest_name: str | None = None) -> str:
    """
    Get a list of reservations, optionally filtered by guest name.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
        guest_name: Optional guest name to filter reservations (partial match supported)

    Returns:
        str: JSON string containing list of reservations with details
    """
    try:
        params = {}
        if guest_name:
            params["guest_name"] = guest_name

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HOTEL_API_BASE_URL}/{process_id}_reservations", params=params)
            response.raise_for_status()
            reservations = response.json()
            return json.dumps(reservations, indent=2)
    except httpx.RequestError as e:
        return f"Error fetching reservations: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing reservations: {e}"


async def get_reservation(process_id: int | str | None = None, reservation_id: int | None = None) -> str:
    """
    Get details of a specific reservation.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
        reservation_id: The ID of the reservation to retrieve

    Returns:
        str: JSON string containing reservation details including hotel, room, guest, dates, and total price
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HOTEL_API_BASE_URL}/{process_id}_reservations/{reservation_id}")
            response.raise_for_status()
            reservation = response.json()
            return json.dumps(reservation, indent=2)
    except httpx.RequestError as e:
        return f"Error fetching reservation: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing reservation: {e}"


async def cancel_reservation(process_id: int | str | None = None, reservation_id: int | None = None) -> str:
    """
    Cancel an existing reservation and free up the room.

    Args:
        process_id: Optional identifier used by callers (e.g. agent/process tracing).
        reservation_id: The ID of the reservation to cancel

    Returns:
        str: Success message confirming the cancellation
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{HOTEL_API_BASE_URL}/{process_id}_reservations/{reservation_id}")
            response.raise_for_status()
            result = response.json()
            return json.dumps(result, indent=2)
    except httpx.RequestError as e:
        return f"Error canceling reservation: {e}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error processing cancellation: {e}"
