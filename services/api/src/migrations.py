from __future__ import annotations

import os
from pathlib import Path

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "packages" / "db" / "migrations"


def apply_migrations() -> None:
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        applied = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            with connection.transaction():
                connection.execute(path.read_text("utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,)
                )
