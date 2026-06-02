from sqlalchemy import create_engine, text

from config import Config
from extensions import db


def ensure_database_exists():
    """Create the configured MySQL database if it does not exist."""
    uri = (
        f"mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}"
        f"@{Config.MYSQL_HOST}/?charset=utf8mb4"
    )
    engine = create_engine(uri)
    with engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DATABASE} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()
    engine.dispose()


def init_db(app):
    """Initialize SQLAlchemy and create tables from models."""
    db.init_app(app)
    import models  # noqa: F401 — enregistre les modeles pour db.create_all()

    with app.app_context():
        db.create_all()
        _ensure_analysis_columns()


def _ensure_analysis_columns():
    """Keep the analyses table compatible with the current model."""
    current_database = Config.MYSQL_DATABASE
    existing_columns_query = text(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :database_name
          AND TABLE_NAME = 'analyses'
        """
    )

    with db.engine.begin() as connection:
        existing_columns = {
            row[0]
            for row in connection.execute(
                existing_columns_query,
                {"database_name": current_database},
            )
        }

        if "analysis_text" not in existing_columns:
            connection.execute(
                text("ALTER TABLE analyses ADD COLUMN analysis_text TEXT NULL")
            )
