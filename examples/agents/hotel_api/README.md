# Hotel API Example

A simple mock hotel booking API for demonstrating agent-based interactions. This FastAPI service manages hotel availability and reservations with data for 15 hotels across 3 Polish cities (Kraków, Warszawa, Gdańsk).

**Note:** This is a mock API with no authentication, payment processing, or real booking functionality.

## Quick Start

### 1. Install Dependencies

```bash
cd examples/agents/hotel_api
uv sync
```

### 2. Set Up Database

```bash
# Create database and populate with mock data
uv run python populate_db.py
```

### 3. Run the API

```bash
uv run uvicorn app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. View interactive docs at `http://localhost:8000/docs`.

## Database Management

### Create Database Schema
```bash
uv run python create_db.py
```
Creates the database schema without any data.

### Populate Database
```bash
uv run python populate_db.py
```
Loads hotel data from `hotel_config.json` into the database. Clears existing data first.

### Clear Database
```bash
uv run python clear_db.py
```
Drops all tables and deletes the database file. Requires confirmation.

## Configuration

Edit `hotel_config.json` to modify hotels, rooms, prices, amenities, and availability. Run `populate_db.py` after making changes.

## API Endpoints

### Cities
- `GET /cities` - List all cities

### Hotels
- `GET /hotels?city=Kraków` - List hotels (optionally filter by city)
- `GET /hotels/{hotel_id}` - Get hotel details with all rooms

### Room Search
- `GET /rooms/available?start_date=2025-01-15&end_date=2025-01-20&city=Warszawa&min_price=300&max_price=500&room_type=deluxe` - Search available rooms with filters

### Reservations
- `POST /reservations` - Create a new reservation
- `GET /reservations?guest_name=Smith` - List reservations (optionally filter by guest)
- `GET /reservations/{reservation_id}` - Get specific reservation
- `DELETE /reservations/{reservation_id}` - Cancel a reservation

## Example Usage

### Search Available Rooms
```bash
curl "http://localhost:8000/rooms/available?start_date=2025-03-01&end_date=2025-03-05&city=Kraków&max_price=400"
```

### Create Reservation
```bash
curl -X POST "http://localhost:8000/reservations" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_id": 3,
    "guest_name": "Jan Kowalski",
    "start_date": "2025-03-10",
    "end_date": "2025-03-12"
  }'
```

## Data Structure

- **3 cities**: Kraków, Warszawa, Gdańsk
- **15 hotels** (5 per city) with varying amenities (spa, pool, gym, etc.)
- **80+ rooms** with different types (standard, deluxe, suite)
- **Prices**: 280-850 PLN per night
- **Availability**: Multiple date windows throughout 2025

## Files

- `app.py` - Main FastAPI application with all endpoints
- `hotel_config.json` - Mock data configuration
- `create_db.py` - Database schema creation script
- `populate_db.py` - Data population script
- `clear_db.py` - Database cleanup script
- `hotel.db` - SQLite database (created automatically)
