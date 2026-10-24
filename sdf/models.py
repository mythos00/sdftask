from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Event:
    """Tədbirin məlumat modeli."""

    title: str
    description: str
    category_id: int
    event_date: date
    event_time: time
    location: str
    max_participants: int


@dataclass(frozen=True)
class User:
    """İstifadəçinin məlumat modeli."""

    id: int
    full_name: str
    email: str
    role: str
