
from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Event:
    title: str
    description: str
    category_id: int
    event_date: date
    event_time: time
    location: str
    max_participants: int


@dataclass(frozen=True)
class User:
    id: int
    full_name: str
    email: str
    role: str
