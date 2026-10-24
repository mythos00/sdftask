
import hashlib
import hmac
import secrets
from datetime import date

from database import Database
from models import Event, User
from validators import (
    ValidationError,
    validate_email,
    validate_event,
    validate_password,
    validate_required,
)


class AuthService:
    """İstifadəçi qeydiyyatı və giriş əməliyyatları."""

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 310_000
        )
        return f"{salt.hex()}${digest.hex()}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt_hex, digest_hex = stored_hash.split("$", 1)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except (ValueError, TypeError):
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 310_000
        )
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def register(full_name: str, email: str, password: str) -> int:
        full_name = validate_required(full_name, "Ad və soyad")
        email = validate_email(email)
        validate_password(password)

        with Database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO users (full_name, email, password_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
                """,
                (full_name, email, AuthService._hash_password(password)),
            ).fetchone()

            if row is None:
                raise ValidationError(
                    "Bu e-poçt ünvanı artıq qeydiyyatdan keçib."
                )

            return row["id"]

    @staticmethod
    def login(email: str, password: str):
        email = validate_email(email)

        with Database.connection() as conn:
            row = conn.execute(
                """
                SELECT id, full_name, email, password_hash, role
                FROM users
                WHERE email = %s
                """,
                (email,),
            ).fetchone()

        if not row or not AuthService._verify_password(
            password, row["password_hash"]
        ):
            raise ValidationError(
                "E-poçt və ya şifrə yanlışdır."
            )

        return User(
            id=row["id"],
            full_name=row["full_name"],
            email=row["email"],
            role=row["role"],
        )


class EventService:
    """Tədbirlərin yaradılması, redaktəsi və axtarışı."""

    @staticmethod
    def categories():
        with Database.connection() as conn:
            return conn.execute(
                "SELECT id, name FROM categories ORDER BY name"
            ).fetchall()

    @staticmethod
    def list_events(
        search="",
        category_id=None,
        location="",
        start_date=None,
        end_date=None,
    ):
        conditions = []
        params = []

        if search.strip():
            conditions.append("e.title ILIKE %s")
            params.append(f"%{search.strip()}%")

        if category_id is not None:
            conditions.append("e.category_id = %s")
            params.append(category_id)

        if location.strip():
            conditions.append("e.location ILIKE %s")
            params.append(f"%{location.strip()}%")

        if start_date:
            conditions.append("e.event_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("e.event_date <= %s")
            params.append(end_date)

        where_sql = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        query = f"""
            SELECT e.id, e.title, e.description, e.category_id,
                   c.name AS category, e.event_date, e.event_time,
                   e.location, e.max_participants,
                   COUNT(r.id)::int AS registered_count
            FROM events e
            JOIN categories c ON c.id = e.category_id
            LEFT JOIN registrations r ON r.event_id = e.id
            {where_sql}
            GROUP BY e.id, c.name
            ORDER BY e.event_date, e.event_time
        """

        with Database.connection() as conn:
            return conn.execute(query, params).fetchall()

    @staticmethod
    def create(event: Event, admin_id: int) -> int:
        validate_event(
            event.title,
            event.description,
            event.location,
            event.event_date,
            event.max_participants,
        )

        with Database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO events (
                    title, description, category_id, event_date,
                    event_time, location, max_participants, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    event.title.strip(),
                    event.description.strip(),
                    event.category_id,
                    event.event_date,
                    event.event_time,
                    event.location.strip(),
                    event.max_participants,
                    admin_id,
                ),
            ).fetchone()

            return row["id"]

    @staticmethod
    def update(event_id: int, event: Event) -> None:
        validate_event(
            event.title,
            event.description,
            event.location,
            event.event_date,
            event.max_participants,
        )

        with Database.connection() as conn:
            conn.execute(
                """
                UPDATE events
                SET title = %s,
                    description = %s,
                    category_id = %s,
                    event_date = %s,
                    event_time = %s,
                    location = %s,
                    max_participants = %s
                WHERE id = %s
                """,
                (
                    event.title.strip(),
                    event.description.strip(),
                    event.category_id,
                    event.event_date,
                    event.event_time,
                    event.location.strip(),
                    event.max_participants,
                    event_id,
                ),
            )

    @staticmethod
    def delete(event_id: int) -> None:
        with Database.connection() as conn:
            conn.execute(
                "DELETE FROM events WHERE id = %s", (event_id,)
            )

    @staticmethod
    def statistics():
        with Database.connection() as conn:
            summary = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM events)::int AS total_events,
                    (SELECT COUNT(*) FROM registrations)::int
                        AS total_registrations,
                    (SELECT COUNT(*) FROM users
                     WHERE role = 'participant')::int AS total_users
                """
            ).fetchone()

            popular = conn.execute(
                """
                SELECT e.title, COUNT(r.id)::int AS registrations
                FROM events e
                LEFT JOIN registrations r ON r.event_id = e.id
                GROUP BY e.id
                ORDER BY registrations DESC, e.title
                LIMIT 5
                """
            ).fetchall()

            by_category = conn.execute(
                """
                SELECT c.name AS category, COUNT(e.id)::int AS total
                FROM categories c
                LEFT JOIN events e ON e.category_id = c.id
                GROUP BY c.id, c.name
                ORDER BY total DESC, c.name
                """
            ).fetchall()

        return summary, popular, by_category


class RegistrationService:
    """Tədbir qeydiyyatını və tutum limitini idarə edir."""

    @staticmethod
    def register(user_id: int, event_id: int) -> None:
        with Database.connection() as conn:
            # Eyni tədbirə paralel qeydiyyatları ardıcıllaşdırır.
            event = conn.execute(
                """
                SELECT id, event_date, max_participants
                FROM events
                WHERE id = %s
                FOR UPDATE
                """,
                (event_id,),
            ).fetchone()

            if not event:
                raise ValidationError("Tədbir tapılmadı.")

            if event["event_date"] < date.today():
                raise ValidationError(
                    "Keçmiş tədbirə qeydiyyat mümkün deyil."
                )

            existing = conn.execute(
                """
                SELECT id FROM registrations
                WHERE user_id = %s AND event_id = %s
                """,
                (user_id, event_id),
            ).fetchone()

            if existing:
                raise ValidationError(
                    "Bu tədbirə artıq qeydiyyatdan keçmisiniz."
                )

            count = conn.execute(
                """
                SELECT COUNT(*)::int AS total
                FROM registrations WHERE event_id = %s
                """,
                (event_id,),
            ).fetchone()["total"]

            if count >= event["max_participants"]:
                raise ValidationError(
                    "Tədbirin iştirakçı limiti dolub."
                )

            conn.execute(
                """
                INSERT INTO registrations (user_id, event_id)
                VALUES (%s, %s)
                """,
                (user_id, event_id),
            )

    @staticmethod
    def cancel(user_id: int, event_id: int) -> bool:
        with Database.connection() as conn:
            result = conn.execute(
                """
                DELETE FROM registrations
                WHERE user_id = %s AND event_id = %s
                RETURNING id
                """,
                (user_id, event_id),
            ).fetchone()

            return result is not None

    @staticmethod
    def my_events(user_id: int):
        with Database.connection() as conn:
            return conn.execute(
                """
                SELECT e.id, e.title, e.event_date, e.event_time,
                       e.location, r.registered_at
                FROM registrations r
                JOIN events e ON e.id = r.event_id
                WHERE r.user_id = %s
                ORDER BY e.event_date, e.event_time
                """,
                (user_id,),
            ).fetchall()
