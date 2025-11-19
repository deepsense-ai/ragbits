"""Script to clear the hotel database - drops all tables and removes the database file."""

from __future__ import annotations

from app import DATABASE_PATH, Base, engine


def clear_database() -> None:
    """Drop all tables and delete the database file."""
    if DATABASE_PATH.exists():
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("Dropped all database tables.")

        # Delete the database file
        DATABASE_PATH.unlink()
        print(f"Deleted database file: {DATABASE_PATH}")

        print("\n" + "=" * 60)
        print("Database cleared successfully!")
        print("=" * 60)
    else:
        print(f"Database file not found: {DATABASE_PATH}")
        print("Nothing to clear.")


if __name__ == "__main__":
    # Ask for confirmation
    print("=" * 60)
    print("WARNING: This will delete all data and the database file!")
    print("=" * 60)
    confirmation = input("Are you sure you want to continue? (yes/no): ")

    if confirmation.lower() in ["yes", "y"]:
        clear_database()
    else:
        print("Operation cancelled.")
