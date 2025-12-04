"""Hotel booking prompt for ragbits agents."""

from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class HotelPromptInput(BaseModel):
    """Defines the structured input schema for the hotel booking prompt."""

    input: str


class HotelPrompt(Prompt[HotelPromptInput]):
    """Prompt for a hotel booking assistant."""

    system_prompt = """
    You are a helpful hotel booking assistant that helps users find and book hotel rooms.
    You can search for available rooms, check hotel details, create reservations, and manage bookings.
    Always be friendly, professional, and provide clear information about hotels, rooms, prices, and availability.
    When making reservations, confirm all details (dates, hotel, room type, guest name) before proceeding.
    """

    user_prompt = """
    {{ input }}
    """
