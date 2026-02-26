from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print("Statsmed API started; database tables ready.")


@app.get("/health")
def health():
    return {"status": "ok"}
