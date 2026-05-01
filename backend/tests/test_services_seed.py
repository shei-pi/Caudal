"""
Tests for app/services/seed.py

Covers `seed_categories`.

The seed function populates the database with a canonical set of expense and income
categories (all marked is_system=True) and attaches CategorizationRule rows for the
well-known merchant patterns.  It is designed to be idempotent: a second call is a
no-op and must not duplicate any data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.services.seed import seed_categories


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Expense categories
# ---------------------------------------------------------------------------


def test_seed_creates_supermercados_expense_category(db):
    """
    seed_categories must create a 'Supermercados' expense category
    (is_income=False, is_system=True).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Supermercados").first()
    assert cat is not None, "Supermercados category must be created"
    assert cat.is_income is False
    assert cat.is_system is True


def test_seed_creates_delivery_expense_category(db):
    """
    seed_categories must create a 'Delivery' expense category.
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Delivery").first()
    assert cat is not None, "Delivery category must be created"
    assert cat.is_income is False
    assert cat.is_system is True


def test_seed_creates_combustible_expense_category(db):
    """
    seed_categories must create a 'Combustible' expense category.
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Combustible").first()
    assert cat is not None, "Combustible category must be created"
    assert cat.is_income is False
    assert cat.is_system is True


def test_seed_creates_salud_expense_category(db):
    """
    seed_categories must create a 'Salud' expense category.
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Salud").first()
    assert cat is not None, "Salud category must be created"
    assert cat.is_income is False
    assert cat.is_system is True


def test_seed_creates_telecomunicaciones_expense_category(db):
    """
    seed_categories must create a 'Telecomunicaciones' expense category.
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Telecomunicaciones").first()
    assert cat is not None, "Telecomunicaciones category must be created"
    assert cat.is_income is False
    assert cat.is_system is True


# ---------------------------------------------------------------------------
# Income categories
# ---------------------------------------------------------------------------


def test_seed_creates_sueldo_income_category(db):
    """
    seed_categories must create a 'Sueldo y haberes' income category
    (is_income=True, is_system=True).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Sueldo y haberes").first()
    assert cat is not None, "Sueldo y haberes category must be created"
    assert cat.is_income is True
    assert cat.is_system is True


def test_seed_creates_multiple_income_categories(db):
    """
    seed_categories must create more than one income category.
    """
    seed_categories(db)

    income_count = (
        db.query(Category)
        .filter(Category.is_income == True, Category.is_system == True)  # noqa: E712
        .count()
    )
    assert income_count >= 2, "At least two income categories must exist after seeding"


# ---------------------------------------------------------------------------
# Categorization rules
# ---------------------------------------------------------------------------


def test_seed_creates_rules_for_supermercados(db):
    """
    The 'Supermercados' category must have at least one CategorizationRule
    after seeding (e.g. CARREFOUR, DIA, etc.).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Supermercados").first()
    assert cat is not None

    rules = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.category_id == cat.id)
        .all()
    )
    assert len(rules) >= 1, "Supermercados must have at least one categorization rule"


def test_seed_creates_rules_for_delivery(db):
    """
    The 'Delivery' category must have at least one CategorizationRule
    after seeding (e.g. PEDIDOSYA, RAPPI, etc.).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Delivery").first()
    assert cat is not None

    rules = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.category_id == cat.id)
        .all()
    )
    assert len(rules) >= 1, "Delivery must have at least one categorization rule"


def test_seed_creates_rules_for_combustible(db):
    """
    The 'Combustible' category must have at least one CategorizationRule
    after seeding (e.g. YPF, SHELL, etc.).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Combustible").first()
    assert cat is not None

    rules = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.category_id == cat.id)
        .all()
    )
    assert len(rules) >= 1, "Combustible must have at least one categorization rule"


def test_seed_creates_rules_for_sueldo(db):
    """
    The 'Sueldo y haberes' income category must have at least one CategorizationRule
    after seeding (e.g. SUELDO, HABERES, etc.).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Sueldo y haberes").first()
    assert cat is not None

    rules = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.category_id == cat.id)
        .all()
    )
    assert len(rules) >= 1, "Sueldo y haberes must have at least one categorization rule"


def test_seed_creates_rules_for_telecomunicaciones(db):
    """
    The 'Telecomunicaciones' category must have at least one CategorizationRule
    after seeding (e.g. MOVISTAR, CLARO, etc.).
    """
    seed_categories(db)

    cat = db.query(Category).filter(Category.name == "Telecomunicaciones").first()
    assert cat is not None

    rules = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.category_id == cat.id)
        .all()
    )
    assert len(rules) >= 1, "Telecomunicaciones must have at least one categorization rule"


def test_seed_total_rules_count_is_non_trivial(db):
    """
    After seeding, there should be a meaningful number of categorization rules
    covering the various merchants — at least 10 rules in total.
    """
    seed_categories(db)

    total_rules = db.query(CategorizationRule).count()
    assert total_rules >= 10, f"Expected at least 10 rules after seeding, got {total_rules}"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_seed_is_idempotent_categories(db):
    """
    Calling seed_categories twice must not create duplicate categories.
    The category count after the second call must equal the count after the first.
    """
    seed_categories(db)
    count_after_first = db.query(Category).count()

    seed_categories(db)
    count_after_second = db.query(Category).count()

    assert count_after_first == count_after_second, (
        "seed_categories must not duplicate categories when called a second time"
    )


def test_seed_is_idempotent_rules(db):
    """
    Calling seed_categories twice must not create duplicate CategorizationRule rows.
    """
    seed_categories(db)
    rules_after_first = db.query(CategorizationRule).count()

    seed_categories(db)
    rules_after_second = db.query(CategorizationRule).count()

    assert rules_after_first == rules_after_second, (
        "seed_categories must not duplicate rules when called a second time"
    )


def test_seed_returns_zero_on_second_call(db):
    """
    seed_categories returns the number of categories created.  On the second call
    (when system categories already exist) it must return 0.
    """
    seed_categories(db)
    result = seed_categories(db)

    assert result == 0, "Second call to seed_categories must return 0 (nothing created)"


def test_seed_returns_positive_count_on_first_call(db):
    """
    seed_categories returns the number of categories created on first call.
    That number must be positive (both expense and income categories are seeded).
    """
    result = seed_categories(db)

    assert result > 0, "First call to seed_categories must return a positive count"
