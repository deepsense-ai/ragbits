"""Script to create the hotel database schema without populating data."""

from __future__ import annotations

from app import DATABASE_PATH, Base, engine


def create_database() -> None:
    """Create all database tables."""
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()
        print(f"Created database file: {DATABASE_PATH}")

    Base.metadata.create_all(bind=engine)
    print("Database schema created successfully!")
    print(f"Location: {DATABASE_PATH}")


if __name__ == "__main__":
    create_database()
