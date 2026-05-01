"""
Shared fixtures and helper functions for Caudal backend tests.

Design notes:
- `engine`, `db`, `client` are pytest fixtures shared via conftest.
- `make_account`, `make_category`, `make_transaction` are plain helper functions
  (not fixtures) so they can be called multiple times with different arguments inside
  a single test.
- `make_transaction` computes hash_fingerprint using the same algorithm as
  `_make_fingerprint` in app/routers/transactions.py so helpers and router agree.
"""

import hashlib
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.utils.text import normalize_description


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def engine():
    """Create a fresh in-memory SQLite engine with all tables for each test.

    StaticPool is required so that all connections (including those opened by
    FastAPI's TestClient in a worker thread) share the same underlying SQLite
    in-memory database.  Without it, each new connection would see a blank DB.
    """
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture(scope="function")
def db(engine):
    """Provide a fresh SQLAlchemy session bound to the in-memory engine."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI TestClient with the real `get_db` dependency overridden to use the
    in-memory test session.  This ensures router tests share the same DB state
    as any helper inserts performed before making HTTP calls.
    """

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper functions (NOT fixtures)
# ---------------------------------------------------------------------------


def _make_fingerprint(tx_date: date, desc_norm: str, amount: float, account_id: int) -> str:
    """
    Replicate the fingerprint logic from app/routers/transactions.py so that
    test-inserted rows pass the duplicate-detection check used by the router.
    """
    raw = f"{tx_date}|{desc_norm}|{round(amount, 2)}|{account_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def make_account(
    db,
    *,
    name: str = "Test Account",
    institution: str = "Banco Test",
    currency: str = "ARS",
    account_type: str = "checking",
    current_balance: float = 0.0,
) -> Account:
    """Insert an Account row and return the flushed (id-bearing) instance."""
    account = Account(
        name=name,
        institution=institution,
        currency=currency,
        account_type=account_type,
        current_balance=current_balance,
        is_active=True,
    )
    db.add(account)
    db.flush()
    return account


def make_category(
    db,
    *,
    name: str = "Test Category",
    color: str = "#6B7280",
    is_income: bool = False,
    is_system: bool = False,
    parent_id: int | None = None,
) -> Category:
    """Insert a Category row and return the flushed instance."""
    cat = Category(
        name=name,
        color=color,
        is_income=is_income,
        is_system=is_system,
        parent_id=parent_id,
    )
    db.add(cat)
    db.flush()
    return cat


def make_transaction(
    db,
    *,
    account_id: int,
    transaction_date: date,
    description: str,
    amount: float,
    tx_type: str = "debit",
    currency: str = "ARS",
    category_id: int | None = None,
    is_recurring: bool = False,
    recurring_group_id: str | None = None,
    transfer_id: str | None = None,
    source: str = "manual",
    notes: str | None = None,
) -> Transaction:
    """
    Insert a Transaction row with a properly computed hash_fingerprint and
    return the flushed instance.  The fingerprint matches what the router
    would compute, so tests that later POST the same data will hit the 409
    duplicate path.
    """
    desc_norm = normalize_description(description)
    fingerprint = _make_fingerprint(transaction_date, desc_norm, amount, account_id)
    tx = Transaction(
        account_id=account_id,
        transaction_date=transaction_date,
        description=description,
        description_normalized=desc_norm,
        amount=amount,
        tx_type=tx_type,
        currency=currency,
        category_id=category_id,
        is_recurring=is_recurring,
        recurring_group_id=recurring_group_id,
        transfer_id=transfer_id,
        hash_fingerprint=fingerprint,
        source=source,
        notes=notes,
    )
    db.add(tx)
    db.flush()
    return tx
