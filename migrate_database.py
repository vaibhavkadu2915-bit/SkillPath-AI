from app.core.database import Base, engine, migrate_legacy_schema
import app.models  # Register all SQLAlchemy models before create_all.


def migrate_database() -> None:
    """Create missing tables and add compatible columns to the old SQLite schema."""
    Base.metadata.create_all(bind=engine)
    migrate_legacy_schema()
    print("Database migration completed. Existing tables and rows were preserved.")


if __name__ == "__main__":
    migrate_database()
