"""
Tests for app/services/recurrence.py

Covers `detect_recurring`.

The algorithm groups transactions by (account_id, normalized_description) and
marks a group as recurring when:
  - The group has >= 3 transactions
  - Intervals between consecutive transactions have coefficient of variation < 0.3
    (i.e. roughly regular spacing ~monthly)
  - Amount coefficient of variation < 0.20 (amounts are stable)

All transactions in a qualifying group receive the same recurring_group_id UUID.
Re-running the function clears the recurring flag from groups that no longer qualify.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.recurrence import detect_recurring
from tests.conftest import make_account, make_transaction


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _monthly_dates(start: date, count: int):
    """Produce `count` dates separated by ~30 days each, starting from `start`."""
    return [start + timedelta(days=30 * i) for i in range(count)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_three_regular_monthly_transactions_flagged_as_recurring(db):
    """
    Three transactions from the same account with the same description and
    regular ~30-day intervals should all be marked is_recurring=True and share
    the same non-null recurring_group_id.
    """
    account = make_account(db)
    start = date(2025, 1, 1)
    dates = _monthly_dates(start, 3)

    txs = [
        make_transaction(
            db,
            account_id=account.id,
            transaction_date=d,
            description="NETFLIX SUSCRIPCION",
            amount=2500,
        )
        for d in dates
    ]
    db.commit()

    detect_recurring(db)
    db.expire_all()

    from app.models.transaction import Transaction
    refreshed = db.query(Transaction).filter(Transaction.account_id == account.id).all()

    assert all(tx.is_recurring for tx in refreshed), "All three transactions should be recurring"
    group_ids = {tx.recurring_group_id for tx in refreshed}
    assert len(group_ids) == 1, "All transactions in the group must share one recurring_group_id"
    assert None not in group_ids, "recurring_group_id must not be None for flagged transactions"


def test_only_two_transactions_not_flagged_as_recurring(db):
    """
    A group of only two transactions is insufficient to establish a recurrence
    pattern; neither transaction should be marked as recurring.
    """
    account = make_account(db)
    start = date(2025, 1, 1)
    dates = _monthly_dates(start, 2)

    for d in dates:
        make_transaction(db, account_id=account.id, transaction_date=d, description="SPOTIFY", amount=1000)
    db.commit()

    detect_recurring(db)
    db.expire_all()

    from app.models.transaction import Transaction
    txs = db.query(Transaction).filter(Transaction.account_id == account.id).all()

    assert not any(tx.is_recurring for tx in txs), "Two transactions are not enough for recurrence"


def test_irregular_intervals_not_flagged_as_recurring(db):
    """
    Three transactions with highly irregular intervals (coefficient of variation >= 0.3)
    should NOT be flagged as recurring.
    """
    account = make_account(db)
    # Intervals: 5, 60, 3 days — very irregular
    d1 = date(2025, 1, 1)
    d2 = d1 + timedelta(days=5)
    d3 = d2 + timedelta(days=60)
    d4 = d3 + timedelta(days=3)

    for d in [d1, d2, d3, d4]:
        make_transaction(db, account_id=account.id, transaction_date=d, description="COMPRA RANDOM", amount=1000)
    db.commit()

    detect_recurring(db)
    db.expire_all()

    from app.models.transaction import Transaction
    txs = db.query(Transaction).filter(Transaction.account_id == account.id).all()

    assert not any(tx.is_recurring for tx in txs), "Irregular intervals should not be flagged"


def test_high_amount_variation_not_flagged_as_recurring(db):
    """
    Three transactions with regular intervals but wildly varying amounts
    (coefficient of variation >= 0.20) should NOT be flagged as recurring.
    """
    account = make_account(db)
    start = date(2025, 1, 1)
    dates = _monthly_dates(start, 3)
    # Amounts with very high variation: 100, 10000, 50
    amounts = [100.0, 10000.0, 50.0]

    for d, amount in zip(dates, amounts):
        make_transaction(db, account_id=account.id, transaction_date=d, description="PAGO VARIABLE", amount=amount)
    db.commit()

    detect_recurring(db)
    db.expire_all()

    from app.models.transaction import Transaction
    txs = db.query(Transaction).filter(Transaction.account_id == account.id).all()

    assert not any(tx.is_recurring for tx in txs), "High amount variation should prevent recurrence flag"


def test_detect_recurring_clears_flags_from_disqualified_transactions(db):
    """
    If a transaction was previously marked as recurring but the group no longer
    qualifies on a subsequent run (because we manually mark it), detect_recurring
    should clear the flag.

    Simulation: insert 3 recurring transactions, run detect_recurring (they get
    flagged), then manually force is_recurring=True on a lone transaction that
    shares no group, and re-run — the lone transaction should end up unflagged.
    """
    account = make_account(db)
    start = date(2025, 1, 1)
    dates = _monthly_dates(start, 3)

    # Group that legitimately qualifies
    for d in dates:
        make_transaction(db, account_id=account.id, transaction_date=d, description="NETFLIX SUSCRIPCION", amount=2500)

    # Lone transaction manually forced to is_recurring=True — should be cleared
    lone = make_transaction(db, account_id=account.id, transaction_date=date(2025, 6, 1), description="COMPRA UNICA VEZ", amount=9999)
    lone.is_recurring = True
    lone.recurring_group_id = "fake-group-id"
    db.commit()

    detect_recurring(db)
    db.expire_all()

    from app.models.transaction import Transaction
    lone_refreshed = db.query(Transaction).filter(Transaction.id == lone.id).first()
    assert lone_refreshed.is_recurring is False, "Lone transaction should have its recurring flag cleared"
    assert lone_refreshed.recurring_group_id is None, "recurring_group_id should be cleared too"


def test_different_accounts_same_description_treated_as_separate_groups(db):
    """
    Transactions from different accounts with the same description must form
    separate recurrence groups (keyed by account_id + description).
    """
    account_a = make_account(db, name="Cuenta A")
    account_b = make_account(db, name="Cuenta B")
    start = date(2025, 1, 1)
    dates = _monthly_dates(start, 3)

    for d in dates:
        make_transaction(db, account_id=account_a.id, transaction_date=d, description="NETFLIX", amount=2500)
        make_transaction(db, account_id=account_b.id, transaction_date=d, description="NETFLIX", amount=2500)
    db.commit()

    detect_recurring(db)
    db.expire_all()

    from app.models.transaction import Transaction
    txs_a = db.query(Transaction).filter(Transaction.account_id == account_a.id).all()
    txs_b = db.query(Transaction).filter(Transaction.account_id == account_b.id).all()

    group_ids_a = {tx.recurring_group_id for tx in txs_a}
    group_ids_b = {tx.recurring_group_id for tx in txs_b}

    # Each account should have its own group
    assert len(group_ids_a) == 1
    assert len(group_ids_b) == 1
    assert group_ids_a != group_ids_b, "Different accounts should produce different group IDs"


def test_detect_recurring_returns_updated_count(db):
    """
    detect_recurring should return the number of transactions whose is_recurring
    value was actually changed during the run.
    """
    account = make_account(db)
    start = date(2025, 1, 1)
    dates = _monthly_dates(start, 3)

    for d in dates:
        make_transaction(db, account_id=account.id, transaction_date=d, description="SPOTIFY", amount=1000)
    db.commit()

    count = detect_recurring(db)

    # All 3 transactions flipped from False -> True
    assert count == 3
