import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite (debug için tek dosya). Test ortamında DATABASE_URL ile override edilebilir.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alanları sonradan eklediğimiz için, mevcut SQLite veritabanında
# eksik kolonları otomatik olarak ekleyen küçük bir migration yardımcı fonksiyonu.
_TASK_COLUMN_DDL = {
    "priority": "ALTER TABLE tasks ADD COLUMN priority VARCHAR DEFAULT 'Normal'",
    "status": "ALTER TABLE tasks ADD COLUMN status VARCHAR DEFAULT 'In-Progress'",
    "deadline": "ALTER TABLE tasks ADD COLUMN deadline VARCHAR",
    "assigned_to": "ALTER TABLE tasks ADD COLUMN assigned_to VARCHAR",
    "title_updated_at": "ALTER TABLE tasks ADD COLUMN title_updated_at FLOAT DEFAULT 0.0",
    "desc_updated_at": "ALTER TABLE tasks ADD COLUMN desc_updated_at FLOAT DEFAULT 0.0",
    "created_at": "ALTER TABLE tasks ADD COLUMN created_at DATETIME",
    "completed_at": "ALTER TABLE tasks ADD COLUMN completed_at DATETIME",
}


def run_lightweight_migrations() -> None:
    """SQLite üzerinde, modelde olup tabloda olmayan kolonları ekler."""
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("tasks")}
    with engine.begin() as conn:
        for column, ddl in _TASK_COLUMN_DDL.items():
            if column not in existing:
                conn.execute(text(ddl))