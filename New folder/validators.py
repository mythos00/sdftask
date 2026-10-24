
import re
from datetime import date


class ValidationError(ValueError):
    """İstifadəçi məlumatlarının yoxlanılması xətası."""


def validate_required(value: str, field_name: str) -> str:
    value = value.strip()

    if not value:
        raise ValidationError(
            f"{field_name} boş saxlanıla bilməz."
        )

    return value


def validate_email(email: str) -> str:
    email = validate_required(email, "E-poçt").lower()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValidationError("Düzgün e-poçt ünvanı daxil edin.")

    return email


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValidationError(
            "Şifrə ən azı 8 simvoldan ibarət olmalıdır."
        )

    return password


def validate_event(
    title: str,
    description: str,
    location: str,
    event_date: date,
    max_participants: int,
) -> None:
    validate_required(title, "Tədbirin adı")
    validate_required(description, "Təsvir")
    validate_required(location, "Keçirilmə yeri")

    if event_date < date.today():
        raise ValidationError(
            "Tədbirin tarixi keçmiş tarix ola bilməz."
        )

    if (
        isinstance(max_participants, bool)
        or not isinstance(max_participants, int)
        or max_participants <= 0
    ):
        raise ValidationError(
            "İştirakçı sayı müsbət tam ədəd olmalıdır."
        )
