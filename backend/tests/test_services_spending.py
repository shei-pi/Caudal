"""
Tests for app/services/spending.py

Covers `get_spending_by_category` and `get_monthly_summary`.

All dates use `date.today()` anchored to the current month so the tests remain
green as time passes without needing static year hard-codes.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.spending import get_monthly_summary, get_spending_by_category
from tests.conftest import make_account, make_category, make_transaction


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_month_date(day: int = 5) -> date:
    """Return a date in the current month at the given day, clamped to today if needed."""
    today = date.today()
    # Clamp to today so the date is never in the future within this month
    target = today.replace(day=day)
    return target if target <= today else today


def _current_month_range() -> tuple[date, date]:
    """Return (first_of_month, today) — use this as explicit date_from/date_to."""
    today = date.today()
    return today.replace(day=1), today


# ---------------------------------------------------------------------------
# get_spending_by_category
# ---------------------------------------------------------------------------


def test_spending_groups_debit_transactions_by_category(db):
    """
    Two debit transactions belonging to the same category should be summed into
    a single CategorySpend item for that category.
    """
    account = make_account(db)
    cat = make_category(db, name="Supermercados")
    today = _current_month_date()

    make_transaction(db, account_id=account.id, transaction_date=today, description="CARREFOUR", amount=1000, category_id=cat.id)
    make_transaction(db, account_id=account.id, transaction_date=today, description="DISCO CABA", amount=500, category_id=cat.id)
    db.commit()

    result = get_spending_by_category(db)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.category_id == cat.id
    assert item.category_name == "Supermercados"
    assert item.total_ars == 1500.0
    assert item.transaction_count == 2


def test_spending_groups_uncategorized_as_sin_categorizar(db):
    """
    Debit transactions without a category_id must appear grouped under the
    sentinel label 'Sin categorizar' with category_id=None.
    """
    account = make_account(db)
    today = _current_month_date()

    make_transaction(db, account_id=account.id, transaction_date=today, description="COMPRA RARA", amount=300, category_id=None)
    db.commit()

    result = get_spending_by_category(db)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.category_id is None
    assert item.category_name == "Sin categorizar"
    assert item.total_ars == 300.0


def test_spending_excludes_credit_transactions(db):
    """
    Credit transactions (income) must NOT appear in the spending report.
    The result should be empty when only credit transactions exist.
    """
    account = make_account(db)
    cat = make_category(db, name="Sueldo", is_income=True)
    today = _current_month_date()

    make_transaction(db, account_id=account.id, transaction_date=today, description="SUELDO MAYO", amount=200000, tx_type="credit", category_id=cat.id)
    db.commit()

    result = get_spending_by_category(db)

    assert result.items == []
    assert result.total_ars == 0.0


def test_spending_excludes_transfer_transactions(db):
    """
    Transfer transactions must NOT be counted as spending.
    """
    account = make_account(db)
    today = _current_month_date()

    make_transaction(db, account_id=account.id, transaction_date=today, description="TRANSFERENCIA CUENTA", amount=5000, tx_type="transfer")
    db.commit()

    result = get_spending_by_category(db)

    assert result.items == []
    assert result.total_ars == 0.0


def test_spending_calculates_percentage_correctly(db):
    """
    Given two categories with 750 and 250 ARS spent, percentages should be 75% and 25%.
    """
    account = make_account(db)
    cat_a = make_category(db, name="Comida")
    cat_b = make_category(db, name="Transporte")
    today = _current_month_date()

    make_transaction(db, account_id=account.id, transaction_date=today, description="SUPERMERCADO", amount=750, category_id=cat_a.id)
    make_transaction(db, account_id=account.id, transaction_date=today, description="UBER", amount=250, category_id=cat_b.id)
    db.commit()

    result = get_spending_by_category(db)

    assert result.total_ars == 1000.0
    by_name = {item.category_name: item for item in result.items}
    assert by_name["Comida"].percentage == 75.0
    assert by_name["Transporte"].percentage == 25.0


def test_spending_filters_by_account_id(db):
    """
    When account_id is provided, only transactions from that account are counted.
    """
    account_a = make_account(db, name="Cuenta A")
    account_b = make_account(db, name="Cuenta B")
    cat = make_category(db, name="Varios")
    today = _current_month_date()

    make_transaction(db, account_id=account_a.id, transaction_date=today, description="COMPRA A", amount=400, category_id=cat.id)
    make_transaction(db, account_id=account_b.id, transaction_date=today, description="COMPRA B", amount=600, category_id=cat.id)
    db.commit()

    result = get_spending_by_category(db, account_id=account_a.id)

    assert result.total_ars == 400.0
    assert result.items[0].transaction_count == 1


def test_spending_filters_by_date_range(db):
    """
    Transactions outside the date_from/date_to window are excluded.
    """
    account = make_account(db)
    cat = make_category(db, name="Varios")
    today = date.today()
    # Use the first of the current month as the in-range date — always <= today
    in_range = today.replace(day=1)
    # Push the out-of-range date to the previous month
    out_of_range = (today.replace(day=1) - timedelta(days=1)).replace(day=15)

    make_transaction(db, account_id=account.id, transaction_date=in_range, description="COMPRA HOY", amount=100, category_id=cat.id)
    make_transaction(db, account_id=account.id, transaction_date=out_of_range, description="COMPRA ANTERIOR", amount=9999, category_id=cat.id)
    db.commit()

    first_of_month = today.replace(day=1)
    result = get_spending_by_category(db, date_from=first_of_month, date_to=today)

    assert result.total_ars == 100.0


def test_spending_items_sorted_by_total_descending(db):
    """
    Items should be returned in descending order of total_ars (highest first).
    """
    account = make_account(db)
    cat_low = make_category(db, name="Café")
    cat_high = make_category(db, name="Supermercado")
    today = _current_month_date()

    make_transaction(db, account_id=account.id, transaction_date=today, description="CAFE CHICO", amount=50, category_id=cat_low.id)
    make_transaction(db, account_id=account.id, transaction_date=today, description="COTO COMPRA", amount=3000, category_id=cat_high.id)
    db.commit()

    result = get_spending_by_category(db)

    assert result.items[0].category_name == "Supermercado"
    assert result.items[1].category_name == "Café"


# ---------------------------------------------------------------------------
# get_monthly_summary
# ---------------------------------------------------------------------------


def test_monthly_summary_separates_income_and_expense(db):
    """
    get_monthly_summary must split credit transactions into income_ars and debit
    transactions into expense_ars, then compute net_ars = income - expense.
    """
    account = make_account(db)
    today = date.today()

    make_transaction(db, account_id=account.id, transaction_date=today, description="SUELDO", amount=100000, tx_type="credit")
    make_transaction(db, account_id=account.id, transaction_date=today, description="ALQUILER", amount=60000, tx_type="debit")
    db.commit()

    result = get_monthly_summary(db, months=1)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.income_ars == 100000.0
    assert item.expense_ars == 60000.0
    assert item.net_ars == 40000.0


def test_monthly_summary_returns_correct_number_of_months(db):
    """
    Requesting N months should return exactly N items in the response.
    """
    result = get_monthly_summary(db, months=6)
    assert len(result.items) == 6


def test_monthly_summary_empty_month_has_zero_values(db):
    """
    A month with no transactions should have income_ars=0, expense_ars=0, net_ars=0.
    """
    result = get_monthly_summary(db, months=1)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.income_ars == 0.0
    assert item.expense_ars == 0.0
    assert item.net_ars == 0.0


def test_monthly_summary_current_month_label_format(db):
    """
    Label should be formatted as 'Mmm YYYY' using the Spanish abbreviated month names.
    """
    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    today = date.today()
    expected_label = f"{month_names[today.month]} {today.year}"

    result = get_monthly_summary(db, months=1)

    assert result.items[0].label == expected_label


def test_monthly_summary_excludes_transfers(db):
    """
    Transfer transactions should not be counted as either income or expense.
    """
    account = make_account(db)
    today = date.today()

    make_transaction(db, account_id=account.id, transaction_date=today, description="TRANSFERENCIA", amount=50000, tx_type="transfer")
    db.commit()

    result = get_monthly_summary(db, months=1)

    item = result.items[0]
    assert item.income_ars == 0.0
    assert item.expense_ars == 0.0
