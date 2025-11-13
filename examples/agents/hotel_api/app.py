from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

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


class Base(DeclarativeBase):
    """Base class for declarative SQLAlchemy models."""

    pass


class Hotel(Base):
    """SQLAlchemy model for a hotel."""

    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    rooms: Mapped[list[Room]] = relationship("Room", back_populates="hotel", cascade="all, delete-orphan")


class Room(Base):
    """SQLAlchemy model for a hotel room."""

    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("hotel_id", "number", name="uq_room_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    number: Mapped[str] = mapped_column(String, nullable=False)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"), nullable=False)

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
    available_date: Mapped[date] = mapped_column(Date, nullable=False)
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
    includes_breakfast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    room: Mapped[Room] = relationship("Room", back_populates="reservations")


class AvailabilityWindow(BaseModel):
    """Continuous date window when a room is available."""

    start: date
    end: date


class RoomAvailabilityResponse(BaseModel):
    """Response payload describing availability for a single room."""

    room_number: str
    available_dates: list[AvailabilityWindow]


class AvailabilityResponse(BaseModel):
    """Response payload for the /availability endpoint."""

    hotel: str
    rooms: list[RoomAvailabilityResponse]


class ReservationRequest(BaseModel):
    """Request body for creating a reservation."""

    hotel: str = Field(..., description="Hotel name (Warsaw, Lodz, or Sosnowiec)")
    room_number: str = Field(..., description="Room number, e.g., 101")
    guest_name: str = Field(..., description="Name for the reservation")
    start_date: date
    end_date: date
    include_breakfast: bool = False


class ReservationResponse(BaseModel):
    """Response payload that represents a reservation."""

    reservation_id: int
    hotel: str
    room_number: str
    start_date: date
    end_date: date
    include_breakfast: bool


class ResetResponse(BaseModel):
    """Generic response body with a single detail message."""

    detail: str


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
    """Load the hotel availability configuration from disk."""
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Config file not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def populate_from_config(session: Session) -> None:
    """Populate the database from the JSON configuration file."""
    config = load_config()
    for hotel_entry in config.get("hotels", []):
        hotel = Hotel(name=hotel_entry["name"])
        session.add(hotel)
        session.flush()

        for room_entry in hotel_entry.get("rooms", []):
            room = Room(number=room_entry["number"], hotel_id=hotel.id)
            session.add(room)
            session.flush()

            for window in room_entry.get("availability", []):
                start = date.fromisoformat(window["start"])
                end = date.fromisoformat(window["end"])
                if end < start:
                    raise ValueError(f"Invalid availability range for room {room.number}: {window}")
                for day in daterange(start, end):
                    session.add(RoomAvailability(room_id=room.id, available_date=day))


def initialize_database() -> None:
    """Create tables and seed the database if it is empty."""
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        has_hotels = session.query(Hotel).first() is not None
        if not has_hotels:
            populate_from_config(session)
            session.commit()


def reset_database() -> None:
    """Drop and rebuild all tables using the configuration file."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        populate_from_config(session)
        session.commit()


app = FastAPI(
    title="RAGBits Hotel API Example",
    version="0.1.0",
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
    """Ensure the SQLite database exists and is seeded on service startup."""
    initialize_database()


@app.get("/hotels", response_model=list[str])
def list_hotels(session: Session = Depends(get_session)) -> list[str]:  # noqa: B008
    """Return the available hotel names."""
    hotels = session.query(Hotel).order_by(Hotel.name).all()
    return [hotel.name for hotel in hotels]


@app.get("/availability", response_model=AvailabilityResponse)
def check_availability(
    hotel: str = Query(..., description="Hotel name"),  # noqa: B008
    start_date: date = Query(..., description="Desired start date"),  # noqa: B008
    end_date: date = Query(..., description="Desired end date"),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> AvailabilityResponse:
    """Return available rooms for the selected hotel and date window."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date.",
        )

    hotel_obj = session.query(Hotel).filter(Hotel.name == hotel).one_or_none()
    if hotel_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel '{hotel}' not found.",
        )

    available_rooms: list[RoomAvailabilityResponse] = []
    for room in hotel_obj.rooms:
        entries = (
            session.query(RoomAvailability)
            .filter(
                RoomAvailability.room_id == room.id,
                RoomAvailability.available_date >= start_date,
                RoomAvailability.available_date <= end_date,
                RoomAvailability.is_reserved.is_(False),
            )
            .order_by(RoomAvailability.available_date)
            .all()
        )
        if entries:
            # Group consecutive dates into windows
            windows: list[AvailabilityWindow] = []
            current_start = entries[0].available_date
            current_end = entries[0].available_date
            for entry in entries[1:]:
                if entry.available_date == current_end + timedelta(days=1):
                    current_end = entry.available_date
                else:
                    windows.append(AvailabilityWindow(start=current_start, end=current_end))
                    current_start = entry.available_date
                    current_end = entry.available_date
            windows.append(AvailabilityWindow(start=current_start, end=current_end))
            available_rooms.append(RoomAvailabilityResponse(room_number=room.number, available_dates=windows))

    return AvailabilityResponse(hotel=hotel_obj.name, rooms=available_rooms)


@app.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    reservation: ReservationRequest,
    session: Session = Depends(get_session),  # noqa: B008
) -> ReservationResponse:
    """Create a reservation if the requested room is available."""
    if reservation.end_date < reservation.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date.",
        )

    hotel_obj = session.query(Hotel).filter(Hotel.name == reservation.hotel).one_or_none()
    if hotel_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel '{reservation.hotel}' not found.",
        )

    room_obj = (
        session.query(Room).filter(Room.hotel_id == hotel_obj.id, Room.number == reservation.room_number).one_or_none()
    )
    if room_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room {reservation.room_number} not found in hotel {reservation.hotel}.",
        )

    availability_entries = (
        session.query(RoomAvailability)
        .filter(
            RoomAvailability.room_id == room_obj.id,
            RoomAvailability.available_date >= reservation.start_date,
            RoomAvailability.available_date <= reservation.end_date,
            RoomAvailability.is_reserved.is_(False),
        )
        .order_by(RoomAvailability.available_date)
        .all()
    )

    expected_nights = (reservation.end_date - reservation.start_date).days + 1
    if len(availability_entries) != expected_nights:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested room is not available for the full date range.",
        )

    for entry in availability_entries:
        entry.is_reserved = True

    reservation_record = Reservation(
        room_id=room_obj.id,
        guest_name=reservation.guest_name,
        start_date=reservation.start_date,
        end_date=reservation.end_date,
        includes_breakfast=reservation.include_breakfast,
    )
    session.add(reservation_record)
    session.commit()
    session.refresh(reservation_record)

    return ReservationResponse(
        reservation_id=reservation_record.id,
        hotel=hotel_obj.name,
        room_number=room_obj.number,
        start_date=reservation_record.start_date,
        end_date=reservation_record.end_date,
        include_breakfast=reservation_record.includes_breakfast,
    )


@app.post("/reset", response_model=ResetResponse)
def reset(session: Session = Depends(get_session)) -> ResetResponse:  # noqa: B008
    """Clear reservations and restore availability from the configuration file."""
    session.close()
    reset_database()
    return ResetResponse(detail="All reservations cleared and availability restored from config.")


@app.get("/reservations", response_model=list[ReservationResponse])
def list_reservations(session: Session = Depends(get_session)) -> list[ReservationResponse]:  # noqa: B008
    """Return all reservations ordered from newest to oldest."""
    reservations = session.query(Reservation).join(Room).join(Hotel).order_by(Reservation.created_at.desc()).all()
    response: list[ReservationResponse] = []
    for entry in reservations:
        response.append(
            ReservationResponse(
                reservation_id=entry.id,
                hotel=entry.room.hotel.name,
                room_number=entry.room.number,
                start_date=entry.start_date,
                end_date=entry.end_date,
                include_breakfast=entry.includes_breakfast,
            )
        )
    return response


@app.delete("/reservations/{reservation_id}", response_model=ResetResponse)
def cancel_reservation(
    reservation_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> ResetResponse:
    """Cancel an existing reservation and free the associated room nights."""
    reservation_obj = session.query(Reservation).filter(Reservation.id == reservation_id).one_or_none()
    if reservation_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} not found.",
        )

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
    return ResetResponse(detail=f"Reservation {reservation_id} canceled.")
