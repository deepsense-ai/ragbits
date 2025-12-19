"""In-memory hotel service for agent scenarios.

This module provides an in-process hotel booking service that uses an in-memory
SQLite database, eliminating the need for a separate HTTP API server.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_CONFIG_PATH = Path(__file__).parent / "hotel_config.json"


# =============================================================================
# SQLAlchemy Models
# =============================================================================


class Base(DeclarativeBase):
    """Base class for declarative SQLAlchemy models."""


class Hotel(Base):
    """SQLAlchemy model for a hotel."""

    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False, index=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    amenities: Mapped[str] = mapped_column(Text, nullable=False)  # JSON stored as text

    rooms: Mapped[list[Room]] = relationship("Room", back_populates="hotel", cascade="all, delete-orphan")


class Room(Base):
    """SQLAlchemy model for a hotel room."""

    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("hotel_id", "number", name="uq_room_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    number: Mapped[str] = mapped_column(String, nullable=False)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"), nullable=False)
    room_type: Mapped[str] = mapped_column(String, nullable=False)  # standard, deluxe, suite
    price_per_night: Mapped[float] = mapped_column(Float, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    amenities: Mapped[str] = mapped_column(Text, nullable=False)  # JSON stored as text

    hotel: Mapped[Hotel] = relationship("Hotel", back_populates="rooms")
    availability: Mapped[list[RoomAvailability]] = relationship(
        "RoomAvailability", back_populates="room", cascade="all, delete-orphan"
    )
    reservations: Mapped[list[Reservation]] = relationship(
        "Reservation", back_populates="room", cascade="all, delete-orphan"
    )


class RoomAvailability(Base):
    """Tracks per-day availability for a specific room."""

    __tablename__ = "room_availability"
    __table_args__ = (UniqueConstraint("room_id", "available_date", name="uq_room_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    available_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_reserved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    room: Mapped[Room] = relationship("Room", back_populates="availability")


class Reservation(Base):
    """Reservation record for a room on specific dates."""

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    room: Mapped[Room] = relationship("Room", back_populates="reservations")


# =============================================================================
# Pydantic Response Models
# =============================================================================


class HotelResponse(BaseModel):
    """Response model for hotel information."""

    id: int
    name: str
    city: str
    address: str
    rating: float
    amenities: list[str]


class RoomResponse(BaseModel):
    """Response model for room information."""

    id: int
    number: str
    room_type: str
    price_per_night: float
    capacity: int
    amenities: list[str]


class HotelDetailResponse(BaseModel):
    """Response model for detailed hotel information including rooms."""

    id: int
    name: str
    city: str
    address: str
    rating: float
    amenities: list[str]
    rooms: list[RoomResponse]


class AvailableRoomResponse(BaseModel):
    """Response for available rooms search."""

    hotel_id: int
    hotel_name: str
    city: str
    room_id: int
    room_number: str
    room_type: str
    price_per_night: float
    capacity: int
    amenities: list[str]


class ReservationRequest(BaseModel):
    """Request body for creating a reservation."""

    hotel_id: int = Field(..., description="Hotel ID")
    room_id: int = Field(..., description="Room ID")
    guest_name: str = Field(..., description="Name for the reservation")
    start_date: date
    end_date: date


class ReservationResponse(BaseModel):
    """Response payload that represents a reservation."""

    reservation_id: int
    hotel_name: str
    city: str
    room_number: str
    room_type: str
    guest_name: str
    start_date: date
    end_date: date
    total_price: float


# =============================================================================
# Utility Functions
# =============================================================================


def daterange(start: date, end: date) -> Generator[date, None, None]:
    """Yield each date between start and end, inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


# =============================================================================
# Hotel Service
# =============================================================================


class HotelService:
    """In-memory hotel booking service.

    This service provides hotel booking functionality using an in-memory SQLite
    database. The database is populated from a JSON configuration file on
    initialization.

    Example:
        >>> service = HotelService()
        >>> cities = service.list_cities()
        >>> hotels = service.list_hotels(city="Kraków")
    """

    def __init__(self, config_path: Path | str | None = None) -> None:
        """Initialize the hotel service with an in-memory database.

        Args:
            config_path: Path to the hotel configuration JSON file.
                        If None, uses the default config path.
        """
        self._config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

        # Create in-memory SQLite database
        self._engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            future=True,
        )
        self._SessionLocal = sessionmaker(bind=self._engine, autoflush=False, autocommit=False)

        # Initialize database schema and populate data
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create database schema and populate with data from config."""
        Base.metadata.create_all(bind=self._engine)
        self._populate_from_config()

    def _populate_from_config(self) -> None:
        """Populate the database from the JSON configuration file."""
        if not self._config_path.exists():
            raise RuntimeError(f"Config file not found at {self._config_path}")

        with self._config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        session = self._SessionLocal()
        try:
            for hotel_data in config.get("hotels", []):
                hotel = Hotel(
                    name=hotel_data["name"],
                    city=hotel_data["city"],
                    address=hotel_data["address"],
                    rating=hotel_data["rating"],
                    amenities=json.dumps(hotel_data["amenities"]),
                )
                session.add(hotel)
                session.flush()

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

                    for window in room_data.get("availability", []):
                        start = date.fromisoformat(window["start"])
                        end = date.fromisoformat(window["end"])

                        if end < start:
                            continue

                        for day in daterange(start, end):
                            availability = RoomAvailability(room_id=room.id, available_date=day, is_reserved=False)
                            session.add(availability)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get_session(self) -> Session:
        """Get a new database session."""
        return self._SessionLocal()

    # -------------------------------------------------------------------------
    # Cities
    # -------------------------------------------------------------------------

    def list_cities(self) -> list[str]:
        """Return all available cities."""
        session = self._get_session()
        try:
            cities = session.query(Hotel.city).distinct().order_by(Hotel.city).all()
            return [city[0] for city in cities]
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Hotels
    # -------------------------------------------------------------------------

    def list_hotels(self, city: str | None = None) -> list[HotelResponse]:
        """Return hotels, optionally filtered by city."""
        session = self._get_session()
        try:
            query = session.query(Hotel)
            if city:
                query = query.filter(Hotel.city == city)
            hotels = query.order_by(Hotel.name).all()

            return [
                HotelResponse(
                    id=hotel.id,
                    name=hotel.name,
                    city=hotel.city,
                    address=hotel.address,
                    rating=hotel.rating,
                    amenities=json.loads(hotel.amenities),
                )
                for hotel in hotels
            ]
        finally:
            session.close()

    def get_hotel_detail(self, hotel_id: int) -> HotelDetailResponse:
        """Get detailed information about a specific hotel including all rooms.

        Raises:
            LookupError: If hotel is not found.
        """
        session = self._get_session()
        try:
            hotel = session.query(Hotel).filter(Hotel.id == hotel_id).one_or_none()
            if hotel is None:
                raise LookupError(f"Hotel with ID {hotel_id} not found.")

            rooms = [
                RoomResponse(
                    id=room.id,
                    number=room.number,
                    room_type=room.room_type,
                    price_per_night=room.price_per_night,
                    capacity=room.capacity,
                    amenities=json.loads(room.amenities),
                )
                for room in hotel.rooms
            ]

            return HotelDetailResponse(
                id=hotel.id,
                name=hotel.name,
                city=hotel.city,
                address=hotel.address,
                rating=hotel.rating,
                amenities=json.loads(hotel.amenities),
                rooms=rooms,
            )
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Room Availability
    # -------------------------------------------------------------------------

    def find_available_rooms(
        self,
        start_date: date,
        end_date: date,
        city: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        room_type: str | None = None,
    ) -> list[AvailableRoomResponse]:
        """Find available rooms matching the search criteria.

        Raises:
            ValueError: If end_date is before start_date.
        """
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")

        session = self._get_session()
        try:
            hotel_query = session.query(Hotel)
            if city:
                hotel_query = hotel_query.filter(Hotel.city == city)

            available_rooms: list[AvailableRoomResponse] = []

            for hotel in hotel_query.all():
                room_query = session.query(Room).filter(Room.hotel_id == hotel.id)

                if min_price is not None:
                    room_query = room_query.filter(Room.price_per_night >= min_price)
                if max_price is not None:
                    room_query = room_query.filter(Room.price_per_night <= max_price)
                if room_type:
                    room_query = room_query.filter(Room.room_type == room_type)

                for room in room_query.all():
                    availability_entries = (
                        session.query(RoomAvailability)
                        .filter(
                            RoomAvailability.room_id == room.id,
                            RoomAvailability.available_date >= start_date,
                            RoomAvailability.available_date <= end_date,
                            RoomAvailability.is_reserved.is_(False),
                        )
                        .count()
                    )

                    expected_nights = (end_date - start_date).days + 1
                    if availability_entries == expected_nights:
                        available_rooms.append(
                            AvailableRoomResponse(
                                hotel_id=hotel.id,
                                hotel_name=hotel.name,
                                city=hotel.city,
                                room_id=room.id,
                                room_number=room.number,
                                room_type=room.room_type,
                                price_per_night=room.price_per_night,
                                capacity=room.capacity,
                                amenities=json.loads(room.amenities),
                            )
                        )

            return available_rooms
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Reservations
    # -------------------------------------------------------------------------

    def create_reservation(
        self,
        hotel_id: int,
        room_id: int,
        guest_name: str,
        start_date: date,
        end_date: date,
    ) -> ReservationResponse:
        """Create a reservation if the requested room is available.

        Raises:
            ValueError: If dates are invalid or room is not available.
            LookupError: If hotel or room is not found.
        """
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date.")

        session = self._get_session()
        try:
            # Verify hotel exists
            hotel = session.query(Hotel).filter(Hotel.id == hotel_id).one_or_none()
            if hotel is None:
                raise LookupError(f"Hotel with ID {hotel_id} not found.")

            # Verify room exists and belongs to hotel
            room = session.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel.id).one_or_none()
            if room is None:
                raise LookupError(f"Room with ID {room_id} not found in hotel {hotel.name}.")

            # Check availability for all requested dates
            availability_entries = (
                session.query(RoomAvailability)
                .filter(
                    RoomAvailability.room_id == room.id,
                    RoomAvailability.available_date >= start_date,
                    RoomAvailability.available_date <= end_date,
                    RoomAvailability.is_reserved.is_(False),
                )
                .all()
            )

            expected_nights = (end_date - start_date).days + 1
            if len(availability_entries) != expected_nights:
                raise ValueError("Requested room is not available for the full date range.")

            # Mark dates as reserved
            for entry in availability_entries:
                entry.is_reserved = True

            # Create reservation
            reservation_record = Reservation(
                room_id=room.id,
                guest_name=guest_name,
                start_date=start_date,
                end_date=end_date,
            )
            session.add(reservation_record)
            session.commit()
            session.refresh(reservation_record)

            # Calculate total price
            total_price = room.price_per_night * expected_nights

            return ReservationResponse(
                reservation_id=reservation_record.id,
                hotel_name=hotel.name,
                city=hotel.city,
                room_number=room.number,
                room_type=room.room_type,
                guest_name=reservation_record.guest_name,
                start_date=reservation_record.start_date,
                end_date=reservation_record.end_date,
                total_price=total_price,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_reservations(self, guest_name: str | None = None) -> list[ReservationResponse]:
        """Return all reservations, optionally filtered by guest name."""
        session = self._get_session()
        try:
            query = session.query(Reservation).join(Room).join(Hotel)

            if guest_name:
                query = query.filter(Reservation.guest_name.ilike(f"%{guest_name}%"))

            reservations = query.order_by(Reservation.created_at.desc()).all()

            response: list[ReservationResponse] = []
            for res in reservations:
                nights = (res.end_date - res.start_date).days + 1
                total_price = res.room.price_per_night * nights

                response.append(
                    ReservationResponse(
                        reservation_id=res.id,
                        hotel_name=res.room.hotel.name,
                        city=res.room.hotel.city,
                        room_number=res.room.number,
                        room_type=res.room.room_type,
                        guest_name=res.guest_name,
                        start_date=res.start_date,
                        end_date=res.end_date,
                        total_price=total_price,
                    )
                )
            return response
        finally:
            session.close()

    def get_reservation(self, reservation_id: int) -> ReservationResponse:
        """Get details of a specific reservation.

        Raises:
            LookupError: If reservation is not found.
        """
        session = self._get_session()
        try:
            reservation = (
                session.query(Reservation).filter(Reservation.id == reservation_id).join(Room).join(Hotel).one_or_none()
            )

            if reservation is None:
                raise LookupError(f"Reservation {reservation_id} not found.")

            nights = (reservation.end_date - reservation.start_date).days + 1
            total_price = reservation.room.price_per_night * nights

            return ReservationResponse(
                reservation_id=reservation.id,
                hotel_name=reservation.room.hotel.name,
                city=reservation.room.hotel.city,
                room_number=reservation.room.number,
                room_type=reservation.room.room_type,
                guest_name=reservation.guest_name,
                start_date=reservation.start_date,
                end_date=reservation.end_date,
                total_price=total_price,
            )
        finally:
            session.close()

    def cancel_reservation(self, reservation_id: int) -> str:
        """Cancel an existing reservation and free the associated room nights.

        Raises:
            LookupError: If reservation is not found.
        """
        session = self._get_session()
        try:
            reservation_obj = session.query(Reservation).filter(Reservation.id == reservation_id).one_or_none()
            if reservation_obj is None:
                raise LookupError(f"Reservation {reservation_id} not found.")

            # Free up the reserved dates
            availability_entries = (
                session.query(RoomAvailability)
                .filter(
                    RoomAvailability.room_id == reservation_obj.room_id,
                    RoomAvailability.available_date >= reservation_obj.start_date,
                    RoomAvailability.available_date <= reservation_obj.end_date,
                )
                .all()
            )
            for entry in availability_entries:
                entry.is_reserved = False

            session.delete(reservation_obj)
            session.commit()
            return f"Reservation {reservation_id} canceled successfully."
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
