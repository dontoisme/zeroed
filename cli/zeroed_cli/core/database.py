"""
Database session management and initialization for Zeroed.
"""

from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional, Union

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, CategoryGroup, Category, DEFAULT_CATEGORIES

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_db_path() -> Path:
    """Get the default database path."""
    # Store in cli/data/budget.db relative to the package
    package_dir = Path(__file__).parent.parent.parent
    data_dir = package_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "budget.db"


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """
    Initialize the database connection and create tables.

    Args:
        db_path: Path to SQLite database file. Defaults to cli/data/budget.db
    """
    global _engine, _SessionLocal

    if db_path is None:
        db_path = get_db_path()

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db_url = f"sqlite:///{db_path}"
    _engine = create_engine(db_url, echo=False)
    _SessionLocal = sessionmaker(bind=_engine)

    # Create all tables
    Base.metadata.create_all(_engine)


def get_engine():
    """Get the SQLAlchemy engine."""
    if _engine is None:
        init_db()
    return _engine


def get_session_factory():
    """Get the session factory."""
    if _SessionLocal is None:
        init_db()
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            session.query(Account).all()
    """
    if _SessionLocal is None:
        init_db()

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_default_categories(session: Session) -> None:
    """
    Create default YNAB-style category groups and categories.

    Only creates if no categories exist yet.
    """
    # Check if categories already exist
    existing = session.query(CategoryGroup).first()
    if existing:
        return

    sort_order = 0
    for group_name, category_names in DEFAULT_CATEGORIES.items():
        # Create group
        group = CategoryGroup(name=group_name, sort_order=sort_order)
        session.add(group)
        session.flush()  # Get the ID

        # Create categories
        for cat_order, cat_name in enumerate(category_names):
            category = Category(
                group_id=group.id,
                name=cat_name,
                sort_order=cat_order
            )
            session.add(category)

        sort_order += 1

    session.commit()


def reset_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """
    Drop all tables and recreate them.

    WARNING: This will delete all data!
    """
    global _engine

    if db_path is None:
        db_path = get_db_path()

    db_path = Path(db_path)

    if db_path.exists():
        db_path.unlink()

    # Reinitialize
    init_db(db_path)
