from contextlib import contextmanager
from pathlib import Path

import psycopg
import streamlit as st
from psycopg.rows import dict_row


class Database:
    """PostgreSQL verilənlər bazası ilə əlaqəni idarə edir."""

    @staticmethod
    def get_connection():
        """Neon PostgreSQL bağlantısı yaradır."""
        try:
            database_url = st.secrets["database"]["url"]

            return psycopg.connect(
                database_url,
                row_factory=dict_row,
                connect_timeout=10,
                sslmode="require",
            )
        except KeyError as exc:
            raise RuntimeError(
                "Database bağlantısı konfiqurasiya edilməyib. "
                ".streamlit/secrets.toml faylını yoxlayın."
            ) from exc
        except psycopg.Error as exc:
            raise RuntimeError(
                "Verilənlər bazasına qoşulmaq mümkün olmadı."
            ) from exc

    @staticmethod
    @contextmanager
    def connection():
        """Sorğunu tranzaksiya daxilində icra edir."""
        with Database.get_connection() as conn:
            yield conn

    @staticmethod
    def initialize():
        """SQL sxemini verilənlər bazasına tətbiq edir."""
        schema_path = Path(__file__).with_name("schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")

        with Database.connection() as conn:
            conn.execute(schema_sql, prepare=False)