"""Script to populate the hotel database from the configuration file."""

from __future__ import annotations

import json
from datetime import date, timedelta

from app import (
    CONFIG_PATH,
    DATABASE_PATH,
    Base,
    Hotel,
    Room,
    RoomAvailability,
    SessionLocal,
    engine,
)


def daterange(start: date, end: date) -> list[date]:
    """Generate a list of dates between start and end, inclusive."""
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def clear_existing_data(session: SessionLocal) -> None:
    """Clear all existing data from the database."""
    # Delete in order to respect foreign key constraints
    session.query(RoomAvailability).delete()
    session.query(Room).delete()
    session.query(Hotel).delete()
    session.commit()
    print("Cleared existing data from database.")


def populate_from_config() -> None:
    """Populate the database from the JSON configuration file."""
    # Ensure database exists
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()
        Base.metadata.create_all(bind=engine)
        print(f"Created new database: {DATABASE_PATH}")

    # Load configuration
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Config file not found at {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    session = SessionLocal()
    try:
        # Clear existing data
        clear_existing_data(session)

        # Populate hotels and rooms
        hotels_count = 0
        rooms_count = 0
        availability_count = 0

        for hotel_data in config.get("hotels", []):
            # Create hotel
            hotel = Hotel(
                name=hotel_data["name"],
                city=hotel_data["city"],
                address=hotel_data["address"],
                rating=hotel_data["rating"],
                amenities=json.dumps(hotel_data["amenities"]),
            )
            session.add(hotel)
            session.flush()
            hotels_count += 1

            # Create rooms
            for room_data in hotel_data.get("rooms", []):
                room = Room(
                    number=room_data["number"],
                    hotel_id=hotel.id,
                    room_type=room_data["room_type"],
                    price_per_night=float(room_data["price_per_night"]),
                    capacity=room_data["capacity"],
                    amenities=json.dumps(room_data["amenities"]),
                )
                session.add(room)
                session.flush()
                rooms_count += 1

                # Create availability windows
                for window in room_data.get("availability", []):
                    start = date.fromisoformat(window["start"])
                    end = date.fromisoformat(window["end"])

                    if end < start:
                        print(f"Warning: Invalid availability range for room {room.number}: {window}")
                        continue

                    for day in daterange(start, end):
                        availability = RoomAvailability(room_id=room.id, available_date=day, is_reserved=False)
                        session.add(availability)
                        availability_count += 1

        session.commit()

        print("\n" + "=" * 60)
        print("Database populated successfully!")
        print("=" * 60)
        print(f"Hotels created:      {hotels_count}")
        print(f"Rooms created:       {rooms_count}")
        print(f"Availability dates:  {availability_count}")
        print("=" * 60)

    except Exception as e:
        session.rollback()
        print(f"Error populating database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    populate_from_config()
