"""
Database Manager Module.
Provides SQLAlchemy engine creation, session factory, context managers,
and DDL execution for SQLite or PostgreSQL databases.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.config_loader import get_config
from src.database.models import Base
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Database Connection Manager.
    Supports SQLite and PostgreSQL engines dynamically based on configuration.
    """

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls, db_url: Optional[str] = None, force_new: bool = False) -> "DatabaseManager":
        if cls._instance is None or force_new or (db_url and db_url != getattr(cls._instance, "db_url", None)):
            instance = super(DatabaseManager, cls).__new__(cls)
            instance._initialize(db_url)
            if not force_new and db_url is None:
                cls._instance = instance
            return instance
        return cls._instance

    def _initialize(self, db_url: Optional[str] = None) -> None:
        config = get_config()

        if db_url is None:
            db_path_str = config.get("paths.database_path", "data/database/mutual_funds.db")
            db_path = Path(db_path_str)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_url = f"sqlite:///{db_path}"
        else:
            self.db_url = db_url

        echo_sql = config.get("database.echo_sql", False)

        logger.info("Initializing Database Engine: %s", self.db_url)

        connect_args = {}
        if self.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(
            self.db_url,
            echo=echo_sql,
            connect_args=connect_args,
            pool_pre_ping=True
        )

        if self.db_url.startswith("sqlite"):
            from sqlalchemy import event
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self) -> None:
        """
        Creates all defined DDL tables in the target database.
        """
        logger.info("Creating Star-Schema tables in database...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("All Star-Schema tables created successfully.")

    def drop_tables(self) -> None:
        """
        Drops all tables in the target database.
        """
        logger.warning("Dropping all existing Star-Schema tables...")
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager that yields an active database session and handles commit/rollback.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("Database session error, rolling back transaction: %s", exc)
            raise
        finally:
            session.close()


def get_db_manager(db_url: Optional[str] = None) -> DatabaseManager:
    return DatabaseManager(db_url)
