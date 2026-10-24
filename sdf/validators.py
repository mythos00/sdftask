import re
from datetime import date


class ValidationError(ValueError):
    """Məlumatların yoxlanılması zamanı yaranan xəta."""


def validate_required(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} mətn formatında olmalıdır."
        )

    value = value.strip()

    if not value:
        raise ValidationError(
            f"{field_name} boş saxlanıla bilməz."
        )

    return value


def validate_email(email: str) -> str:
    email = validate_required(email, "E-poçt").lower()

    if len(email) > 255:
        raise ValidationError(
            "E-poçt ünvanı çox uzundur."
        )

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValidationError(
            "Düzgün e-poçt ünvanı daxil edin."
        )

    return email


def validate_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 8:
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

    title = validate_required(
        title,
        "Tədbirin adı"
    )

    description = validate_required(
        description,
        "Təsvir"
    )

    location = validate_required(
        location,
        "Keçirilmə yeri"
    )

    if len(title) > 200:
        raise ValidationError(
            "Tədbirin adı 200 simvoldan çox ola bilməz."
        )

    if len(location) > 200:
        raise ValidationError(
            "Keçirilmə yeri 200 simvoldan çox ola bilməz."
        )

    if not isinstance(event_date, date):
        raise ValidationError(
            "Tədbirin tarixi düzgün göstərilməyib."
        )

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
