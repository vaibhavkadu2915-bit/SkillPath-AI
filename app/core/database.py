import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("SKILLPATH_DATABASE_URL", "sqlite:///./skillpath.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def migrate_legacy_schema():
    """Add prototype fields to the original SQLite tables without replacing data."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    additions = {
        "users": {
            "password_hash": "VARCHAR",
            "phone": "VARCHAR",
            "education": "TEXT",
            "links": "TEXT",
            "created_at": "DATETIME",
        },
        "certificates": {
            "title": "VARCHAR",
            "issuer": "VARCHAR",
            "issue_date": "VARCHAR",
            "cert_type": "VARCHAR",
            "credential_id": "VARCHAR",
            "created_at": "DATETIME",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }
            for name, sql_type in columns.items():
                if existing and name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"
                    )
