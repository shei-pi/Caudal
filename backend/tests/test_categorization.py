import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.services.categorization import apply_rules
from app.utils.text import normalize_description


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_contains_rule(db):
    cat = Category(name="Supermercados", color="#10B981", is_income=False, is_system=True)
    db.add(cat)
    db.flush()

    rule = CategorizationRule(
        category_id=cat.id, pattern="CARREFOUR", match_type="contains", priority=0, is_active=True
    )
    db.add(rule)
    db.commit()

    tx = Transaction(
        account_id=1,
        transaction_date="2024-01-01",
        description="CARREFOUR PALERMO",
        description_normalized=normalize_description("CARREFOUR PALERMO"),
        amount=5000,
        tx_type="debit",
        currency="ARS",
        hash_fingerprint="abc123",
        source="manual",
    )

    result = apply_rules(db, tx)
    assert result == cat.id


def test_regex_rule(db):
    cat = Category(name="Combustible", color="#6366F1", is_income=False, is_system=True)
    db.add(cat)
    db.flush()

    rule = CategorizationRule(
        category_id=cat.id,
        pattern=r"YPF|SHELL|AXION",
        match_type="regex",
        priority=1,
        is_active=True,
    )
    db.add(rule)
    db.commit()

    tx = Transaction(
        account_id=1,
        transaction_date="2024-01-01",
        description="YPF ESTACION 123",
        description_normalized=normalize_description("YPF ESTACION 123"),
        amount=10000,
        tx_type="debit",
        currency="ARS",
        hash_fingerprint="def456",
        source="manual",
    )

    result = apply_rules(db, tx)
    assert result == cat.id


def test_no_match_returns_none(db):
    tx = Transaction(
        account_id=1,
        transaction_date="2024-01-01",
        description="COMPRA GENERICA SIN REGLA",
        description_normalized=normalize_description("COMPRA GENERICA SIN REGLA"),
        amount=100,
        tx_type="debit",
        currency="ARS",
        hash_fingerprint="ghi789",
        source="manual",
    )
    result = apply_rules(db, tx)
    assert result is None
