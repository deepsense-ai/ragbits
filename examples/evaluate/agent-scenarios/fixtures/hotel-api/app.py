"""FastAPI application implementing a hotel availability and reservation API."""

from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
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
# Configuration & Database Setup
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "hotel_config.json"
DATABASE_PATH = BASE_DIR / "hotel.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    room: Mapped[Room] = relationship("Room", back_populates="reservations")


# =============================================================================
# Pydantic Schemas
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


class AvailabilityWindow(BaseModel):
    """Continuous date window when a room is available."""

    start: date
    end: date


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


class MessageResponse(BaseModel):
    """Generic response body with a single detail message."""

    detail: str


# =============================================================================
# Utility Functions
# =============================================================================


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session that is closed afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def daterange(start: date, end: date) -> Generator[date, None, None]:
    """Yield each date between start and end, inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def load_config() -> dict:
    """Load the hotel configuration from disk."""
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Config file not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def initialize_database() -> None:
    """Create tables if they don't exist. Does not populate data."""
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()
    Base.metadata.create_all(bind=engine)


@lru_cache(maxsize=64)
def get_namespaced_models(namespace: str) -> tuple:
    """Return namespaced model classes & base for a given namespace.

    This dynamically creates a new DeclarativeBase subclass and models
    with tables suffixed by the namespace so multiple separate table sets
    may coexist in a single SQLite file.
    """

    class NamespacedBase(DeclarativeBase):
        pass

    class HotelNS(NamespacedBase):
        __tablename__ = f"hotels_{namespace}"

        id: Mapped[int] = mapped_column(primary_key=True, index=True)
        name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        city: Mapped[str] = mapped_column(String, nullable=False, index=True)
        address: Mapped[str] = mapped_column(String, nullable=False)
        rating: Mapped[float] = mapped_column(Float, nullable=False)
        amenities: Mapped[str] = mapped_column(Text, nullable=False)

        rooms: Mapped[list] = relationship("RoomNS", back_populates="hotel", cascade="all, delete-orphan")

    class RoomNS(NamespacedBase):
        __tablename__ = f"rooms_{namespace}"
        __table_args__ = (UniqueConstraint("hotel_id", "number", name=f"uq_room_number_{namespace}"),)

        id: Mapped[int] = mapped_column(primary_key=True, index=True)
        number: Mapped[str] = mapped_column(String, nullable=False)
        hotel_id: Mapped[int] = mapped_column(ForeignKey(HotelNS.__tablename__ + ".id"), nullable=False)
        room_type: Mapped[str] = mapped_column(String, nullable=False)
        price_per_night: Mapped[float] = mapped_column(Float, nullable=False)
        capacity: Mapped[int] = mapped_column(Integer, nullable=False)
        amenities: Mapped[str] = mapped_column(Text, nullable=False)

        hotel: Mapped[HotelNS] = relationship("HotelNS", back_populates="rooms")
        availability: Mapped[list] = relationship(
            "RoomAvailabilityNS", back_populates="room", cascade="all, delete-orphan"
        )
        reservations: Mapped[list] = relationship("ReservationNS", back_populates="room", cascade="all, delete-orphan")

    class RoomAvailabilityNS(NamespacedBase):
        __tablename__ = f"room_availability_{namespace}"
        __table_args__ = (UniqueConstraint("room_id", "available_date", name=f"uq_room_date_{namespace}"),)

        id: Mapped[int] = mapped_column(primary_key=True, index=True)
        room_id: Mapped[int] = mapped_column(ForeignKey(RoomNS.__tablename__ + ".id"), nullable=False)
        available_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
        is_reserved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

        room: Mapped[RoomNS] = relationship("RoomNS", back_populates="availability")

    class ReservationNS(NamespacedBase):
        __tablename__ = f"reservations_{namespace}"

        id: Mapped[int] = mapped_column(primary_key=True, index=True)
        room_id: Mapped[int] = mapped_column(ForeignKey(RoomNS.__tablename__ + ".id"), nullable=False)
        guest_name: Mapped[str] = mapped_column(String, nullable=False)
        start_date: Mapped[date] = mapped_column(Date, nullable=False)
        end_date: Mapped[date] = mapped_column(Date, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

        room: Mapped[RoomNS] = relationship("RoomNS", back_populates="reservations")

    return NamespacedBase, HotelNS, RoomNS, RoomAvailabilityNS, ReservationNS


def ensure_namespaced_tables(namespace: str) -> None:
    """Create the namespaced tables for the given namespace if they don't exist."""
    NamespacedBase, *_ = get_namespaced_models(str(namespace))
    NamespacedBase.metadata.create_all(bind=engine)


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="RAGBits Hotel API Example",
    version="0.2.0",
    description="Simple hotel availability and reservation API backed by SQLite.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the SQLite database schema exists on service startup."""
    initialize_database()


# =============================================================================
# API Endpoints - Cities
# =============================================================================


@app.get("/{pid}_cities", response_model=list[str])
def list_cities(pid: int, session: Session = Depends(get_session)) -> list[str]:  # noqa: B008
    """Return all available cities."""
    ensure_namespaced_tables(pid)
    _, HotelNS, *_ = get_namespaced_models(str(pid))

    cities = session.query(HotelNS.city).distinct().order_by(HotelNS.city).all()
    return [city[0] for city in cities]


# =============================================================================
# API Endpoints - Hotels
# =============================================================================


@app.get("/{pid}_hotels", response_model=list[HotelResponse])
def list_hotels(
    pid: int,
    city: str | None = Query(None, description="Filter by city"),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[HotelResponse]:
    """Return hotels, optionally filtered by city."""
    ensure_namespaced_tables(pid)
    _, HotelNS, *_ = get_namespaced_models(str(pid))

    query = session.query(HotelNS)
    if city:
        query = query.filter(HotelNS.city == city)
    hotels = query.order_by(HotelNS.name).all()

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


@app.get("/{pid}_hotels/{hotel_id}", response_model=HotelDetailResponse)
def get_hotel_detail(
    pid: int,
    hotel_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> HotelDetailResponse:
    """Get detailed information about a specific hotel including all rooms."""
    ensure_namespaced_tables(pid)
    _, HotelNS, *_ = get_namespaced_models(str(pid))

    hotel = session.query(HotelNS).filter(HotelNS.id == hotel_id).one_or_none()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID {hotel_id} not found.",
        )

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


# =============================================================================
# API Endpoints - Room Availability
# =============================================================================


@app.get("/{pid}_rooms/available", response_model=list[AvailableRoomResponse])
def find_available_rooms(
    pid: int,
    start_date: date = Query(..., description="Check-in date"),  # noqa: B008
    end_date: date = Query(..., description="Check-out date"),  # noqa: B008
    city: str | None = Query(None, description="Filter by city"),  # noqa: B008
    min_price: float | None = Query(None, description="Minimum price per night"),  # noqa: B008
    max_price: float | None = Query(None, description="Maximum price per night"),  # noqa: B008
    room_type: str | None = Query(None, description="Filter by room type (standard, deluxe, suite)"),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[AvailableRoomResponse]:
    """Find available rooms matching the search criteria."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date.",
        )

    ensure_namespaced_tables(pid)
    _, HotelNS, RoomNS, RoomAvailabilityNS, *_ = get_namespaced_models(str(pid))

    # Build hotel query with filters
    hotel_query = session.query(HotelNS)
    if city:
        hotel_query = hotel_query.filter(Hotel.city == city)

    available_rooms: list[AvailableRoomResponse] = []

    for hotel in hotel_query.all():
        room_query = session.query(RoomNS).filter(RoomNS.hotel_id == hotel.id)

        # Apply room filters
        if min_price is not None:
            room_query = room_query.filter(Room.price_per_night >= min_price)
        if max_price is not None:
            room_query = room_query.filter(Room.price_per_night <= max_price)
        if room_type:
            room_query = room_query.filter(Room.room_type == room_type)

        for room in room_query.all():
            # Check if room is available for all requested dates
            availability_entries = (
                session.query(RoomAvailabilityNS)
                .filter(
                    RoomAvailabilityNS.room_id == room.id,
                    RoomAvailabilityNS.available_date >= start_date,
                    RoomAvailabilityNS.available_date <= end_date,
                    RoomAvailabilityNS.is_reserved.is_(False),
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


# =============================================================================
# API Endpoints - Reservations
# =============================================================================


@app.post("/{pid}_reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    pid: int,
    reservation: ReservationRequest,
    session: Session = Depends(get_session),  # noqa: B008
) -> ReservationResponse:
    """Create a reservation if the requested room is available."""
    if reservation.end_date < reservation.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date.",
        )

    # Resolve namespaced models and ensure tables exist
    ensure_namespaced_tables(pid)
    _, HotelNS, RoomNS, RoomAvailabilityNS, ReservationNS = get_namespaced_models(str(pid))

    # Verify hotel exists
    hotel = session.query(HotelNS).filter(HotelNS.id == reservation.hotel_id).one_or_none()
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with ID {reservation.hotel_id} not found.",
        )

    # Verify room exists and belongs to hotel
    room = session.query(RoomNS).filter(RoomNS.id == reservation.room_id, RoomNS.hotel_id == hotel.id).one_or_none()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {reservation.room_id} not found in hotel {hotel.name}.",
        )

    # Check availability for all requested dates
    availability_entries = (
        session.query(RoomAvailabilityNS)
        .filter(
            RoomAvailabilityNS.room_id == room.id,
            RoomAvailabilityNS.available_date >= reservation.start_date,
            RoomAvailabilityNS.available_date <= reservation.end_date,
            RoomAvailabilityNS.is_reserved.is_(False),
        )
        .all()
    )

    expected_nights = (reservation.end_date - reservation.start_date).days + 1
    if len(availability_entries) != expected_nights:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested room is not available for the full date range.",
        )

    # Mark dates as reserved
    for entry in availability_entries:
        entry.is_reserved = True

    # Create reservation
    reservation_record = ReservationNS(
        room_id=room.id,
        guest_name=reservation.guest_name,
        start_date=reservation.start_date,
        end_date=reservation.end_date,
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


@app.get("/{pid}_reservations", response_model=list[ReservationResponse])
def list_reservations(
    pid: int,
    guest_name: str | None = Query(None, description="Filter by guest name"),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[ReservationResponse]:
    """Return all reservations, optionally filtered by guest name."""
    ensure_namespaced_tables(pid)
    _, HotelNS, RoomNS, *_ = get_namespaced_models(str(pid))
    ReservationNS = get_namespaced_models(str(pid))[4]

    query = session.query(ReservationNS).join(RoomNS).join(HotelNS)

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


@app.get("/{pid}_reservations/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    pid: int,
    reservation_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> ReservationResponse:
    """Get details of a specific reservation."""
    ensure_namespaced_tables(pid)
    _, HotelNS, RoomNS, *_ = get_namespaced_models(str(pid))
    ReservationNS = get_namespaced_models(str(pid))[4]

    reservation = (
        session.query(ReservationNS).filter(ReservationNS.id == reservation_id).join(RoomNS).join(HotelNS).one_or_none()
    )

    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} not found.",
        )

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


@app.delete("/{pid}_reservations/{reservation_id}", response_model=MessageResponse)
def cancel_reservation(
    pid: int,
    reservation_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> MessageResponse:
    """Cancel an existing reservation and free the associated room nights."""
    ensure_namespaced_tables(pid)
    _, RoomAvailabilityNS, ReservationNS = get_namespaced_models(str(pid))

    reservation_obj = session.query(ReservationNS).filter(ReservationNS.id == reservation_id).one_or_none()
    if reservation_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} not found.",
        )

    # Free up the reserved dates
    availability_entries = (
        session.query(RoomAvailabilityNS)
        .filter(
            RoomAvailabilityNS.room_id == reservation_obj.room_id,
            RoomAvailabilityNS.available_date >= reservation_obj.start_date,
            RoomAvailabilityNS.available_date <= reservation_obj.end_date,
        )
        .all()
    )
    for entry in availability_entries:
        entry.is_reserved = False

    session.delete(reservation_obj)
    session.commit()
    return MessageResponse(detail=f"Reservation {reservation_id} canceled successfully.")
