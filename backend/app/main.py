from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    accounts,
    analytics,
    categories,
    exchange_rates,
    holdings,
    imports,
    instruments,
    rules,
    transactions,
)
from app.services.seed import seed_categories


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        seed_categories(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Caudal API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(rules.router)
app.include_router(exchange_rates.router)
app.include_router(instruments.router)
app.include_router(holdings.router)
app.include_router(analytics.router)
app.include_router(imports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
