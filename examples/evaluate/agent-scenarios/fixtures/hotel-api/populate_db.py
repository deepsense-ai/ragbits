"""Script to populate the hotel database from the configuration file."""

import json
from datetime import date, timedelta

from app import CONFIG_PATH, DATABASE_PATH, SessionLocal, ensure_namespaced_tables, get_namespaced_models
from sqlalchemy.orm import Session


def daterange(start: date, end: date) -> list[date]:
    """Generate a list of dates between start and end, inclusive."""
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def clear_existing_data(session: Session, HotelModel: type, RoomModel: type, RoomAvailabilityModel: type) -> None:
    """Clear all existing data from the database."""
    # Delete in order to respect foreign key constraints
    session.query(RoomAvailabilityModel).delete()
    session.query(RoomModel).delete()
    session.query(HotelModel).delete()
    session.commit()
    print("Cleared existing data from database.")


def _ensure_database_file() -> None:
    """Ensure the SQLite database file exists (no tables created here)."""
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()
        print(f"Created new database file: {DATABASE_PATH}")


def populate_from_config(ids: list[int]) -> None:
    """Populate the database for each namespace ID in `ids` using the JSON config file.

    For each id a separate set of tables (hotels_{id}, rooms_{id}, etc.) will be
    created and populated in the same SQLite database file.
    """
    _ensure_database_file()

    # Load configuration
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Config file not found at {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)

    # We'll run the populate flow once for each namespace id.
    for ns in ids:
        ns_str = str(ns)
        print(f"\nPopulating namespace: {ns_str}")

        # Ensure tables for this namespace exist
        ensure_namespaced_tables(ns_str)

        _, HotelModel, RoomModel, RoomAvailabilityModel, _ = get_namespaced_models(ns_str)

        session = SessionLocal()
        try:
            # Clear any existing data in this namespace
            clear_existing_data(session, HotelModel, RoomModel, RoomAvailabilityModel)

            # Counters for this namespace
            hotels_count = 0
            rooms_count = 0
            availability_count = 0

            for hotel_data in config.get("hotels", []):
                # Create hotel
                hotel = HotelModel(
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
                    room = RoomModel(
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
                            availability = RoomAvailabilityModel(room_id=room.id, available_date=day, is_reserved=False)
                            session.add(availability)
                            availability_count += 1

            session.commit()

            print("\n" + "=" * 60)
            print(f"Namespace {ns_str} populated successfully!")
            print("=" * 60)
            print(f"Hotels created:      {hotels_count}")
            print(f"Rooms created:       {rooms_count}")
            print(f"Availability dates:  {availability_count}")
            print("=" * 60)

        except Exception as e:
            session.rollback()
            print(f"Error populating namespace {ns_str}: {e}")
            raise
        finally:
            session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate hotel tables for namespaces from config")
    parser.add_argument(
        "--ids",
        type=int,
        nargs="+",
        help="List of integer namespace ids to populate (e.g. --ids 1 2 3)",
    )

    args = parser.parse_args()
    ids = args.ids or [1]
    populate_from_config(ids)
