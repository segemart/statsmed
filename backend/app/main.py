from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .db.database import engine
from .db.models import Base
from .routers import auth, data, quality

app = FastAPI(
    title="Statsmed API",
    description="Statistics for medical data analysis — upload data, run tests, persist results.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(data.router)
app.include_router(quality.router)


def _run_migrations():
    """Add columns that create_all cannot add to already-existing tables."""
    insp = inspect(engine)
    migrations = [
        ("quality_control_operations", "is_public", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("quality_control_operations", "last_sample_json", "TEXT"),
        ("quality_control_runs", "sample_date", "TIMESTAMP"),
    ]
    with engine.begin() as conn:
        for table, column, col_def in migrations:
            if table in insp.get_table_names():
                existing = [c["name"] for c in insp.get_columns(table)]
                if column not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_def}'))
                    print(f"  Migration: added {table}.{column}")


@app.on_event("startup")
def on_startup():
    _run_migrations()
    Base.metadata.create_all(bind=engine)
    print("Statsmed API started; database tables ready.")


@app.get("/health")
def health():
    return {"status": "ok"}
