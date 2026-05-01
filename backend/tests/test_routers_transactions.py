"""
Tests for app/routers/transactions.py

Documents the HTTP API for transactions via FastAPI TestClient.

The `client` fixture from conftest overrides `get_db` with an in-memory SQLite
session, so every test runs in full isolation against a real (but ephemeral) DB.

Transactions API surface:
  POST   /api/transactions                — create transaction (201)
  GET    /api/transactions                — paginated list with filters
  GET    /api/transactions/{id}           — get single transaction
  PUT    /api/transactions/{id}           — update fields
  DELETE /api/transactions/{id}           — delete (cascades both transfer legs)

Key invariants:
  - Fingerprint deduplication: same date+description+amount+account → 409
  - tx_type="transfer" creates TWO linked rows sharing a transfer_id UUID
  - tx_type="transfer" without to_account_id → 422
  - Auto-categorization is applied on create when matching rules exist
  - currency defaults to "ARS"
"""

from datetime import date, timedelta

from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from tests.conftest import make_account, make_category, make_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_tx(account_id: int, *, description: str = "COMPRA EJEMPLO", amount: float = 1000.0, tx_type: str = "debit") -> dict:
    """Build a minimal valid TransactionCreate payload."""
    return {
        "account_id": account_id,
        "transaction_date": str(date.today()),
        "description": description,
        "amount": amount,
        "tx_type": tx_type,
        "currency": "ARS",
    }


# ---------------------------------------------------------------------------
# POST /api/transactions — create
# ---------------------------------------------------------------------------


def test_create_transaction_returns_201(client, db):
    """
    A well-formed POST body must create a transaction and return HTTP 201 with
    the persisted transaction data including id and system fields.
    """
    account = make_account(db)
    db.commit()

    response = client.post("/api/transactions", json=_base_tx(account.id))
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["account_id"] == account.id
    assert data["description"] == "COMPRA EJEMPLO"
    assert data["amount"] == 1000.0
    assert data["tx_type"] == "debit"
    assert data["currency"] == "ARS"
    assert "hash_fingerprint" in data
    assert "created_at" in data


def test_create_transaction_stores_description_normalized(client, db):
    """
    The router must normalize the description (uppercase, strip accents) and
    persist it in `description_normalized`.
    """
    account = make_account(db)
    db.commit()

    response = client.post(
        "/api/transactions",
        json=_base_tx(account.id, description="compra en café palermo"),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["description_normalized"] == "COMPRA EN CAFE PALERMO"


def test_create_transaction_default_currency_is_ars(client, db):
    """
    When no currency is specified, it must default to 'ARS'.
    """
    account = make_account(db)
    db.commit()

    payload = _base_tx(account.id)
    del payload["currency"]
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201
    assert response.json()["currency"] == "ARS"


# ---------------------------------------------------------------------------
# POST — auto-categorization
# ---------------------------------------------------------------------------


def test_create_transaction_auto_categorizes_via_rule(client, db):
    """
    When a matching CategorizationRule exists at creation time, the transaction
    must be automatically assigned the corresponding category_id.
    """
    account = make_account(db)
    cat = Category(name="Supermercados", color="#10B981", is_income=False, is_system=True)
    db.add(cat)
    db.flush()
    rule = CategorizationRule(
        category_id=cat.id,
        pattern="CARREFOUR",
        match_type="contains",
        priority=0,
        is_active=True,
    )
    db.add(rule)
    db.commit()

    response = client.post(
        "/api/transactions",
        json=_base_tx(account.id, description="CARREFOUR PALERMO 1234"),
    )
    assert response.status_code == 201
    assert response.json()["category_id"] == cat.id


def test_create_transaction_no_rule_leaves_category_null(client, db):
    """
    When no rule matches the description, category_id must be None.
    """
    account = make_account(db)
    db.commit()

    response = client.post(
        "/api/transactions",
        json=_base_tx(account.id, description="COMPRA DESCONOCIDA"),
    )
    assert response.status_code == 201
    assert response.json()["category_id"] is None


def test_create_transaction_explicit_category_is_respected(client, db):
    """
    When `category_id` is explicitly provided, it must be stored as-is even if
    a matching rule would assign a different category.
    """
    account = make_account(db)
    cat_explicit = make_category(db, name="Categoría manual")
    cat_rule = Category(name="Supermercados", color="#10B981", is_income=False, is_system=True)
    db.add(cat_rule)
    db.flush()
    rule = CategorizationRule(
        category_id=cat_rule.id,
        pattern="CARREFOUR",
        match_type="contains",
        priority=0,
        is_active=True,
    )
    db.add(rule)
    db.commit()

    payload = _base_tx(account.id, description="CARREFOUR PALERMO")
    payload["category_id"] = cat_explicit.id
    response = client.post("/api/transactions", json=payload)

    assert response.status_code == 201
    assert response.json()["category_id"] == cat_explicit.id


# ---------------------------------------------------------------------------
# POST — duplicate detection (409)
# ---------------------------------------------------------------------------


def test_create_transaction_duplicate_returns_409(client, db):
    """
    Creating a transaction with the same date, description, amount, and account
    as an existing transaction must return HTTP 409 (Conflict).
    """
    account = make_account(db)
    db.commit()

    payload = _base_tx(account.id)
    client.post("/api/transactions", json=payload)  # first

    response = client.post("/api/transactions", json=payload)  # duplicate
    assert response.status_code == 409


def test_create_transaction_same_description_different_amount_is_not_duplicate(client, db):
    """
    Transactions with the same description but different amounts are distinct;
    the second one must be created successfully (201).
    """
    account = make_account(db)
    db.commit()

    client.post("/api/transactions", json=_base_tx(account.id, amount=1000.0))
    response = client.post("/api/transactions", json=_base_tx(account.id, amount=2000.0))
    assert response.status_code == 201


def test_create_transaction_same_description_different_account_is_not_duplicate(client, db):
    """
    The fingerprint includes account_id, so the same description+amount on a
    different account must succeed (201).
    """
    account_a = make_account(db, name="Cuenta A", institution="Banco")
    account_b = make_account(db, name="Cuenta B", institution="Banco")
    db.commit()

    client.post("/api/transactions", json=_base_tx(account_a.id))
    response = client.post("/api/transactions", json=_base_tx(account_b.id))
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST — transfers
# ---------------------------------------------------------------------------


def test_create_transfer_creates_two_linked_transactions(client, db):
    """
    POST with tx_type="transfer" and a valid to_account_id must create TWO
    Transaction rows, both sharing the same non-null transfer_id UUID.
    """
    account_a = make_account(db, name="Cuenta A", institution="Banco")
    account_b = make_account(db, name="Cuenta B", institution="Banco")
    db.commit()

    payload = {
        "account_id": account_a.id,
        "transaction_date": str(date.today()),
        "description": "Transferencia entre cuentas",
        "amount": 5000.0,
        "tx_type": "transfer",
        "currency": "ARS",
        "to_account_id": account_b.id,
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201
    transfer_id = response.json()["transfer_id"]
    assert transfer_id is not None

    # Both sides must exist with the same transfer_id
    all_txs = client.get("/api/transactions").json()["items"]
    with_transfer_id = [tx for tx in all_txs if tx["transfer_id"] == transfer_id]
    assert len(with_transfer_id) == 2


def test_create_transfer_has_one_leg_per_account(client, db):
    """
    The outgoing leg must be on account_id and the incoming leg on to_account_id.
    """
    account_a = make_account(db, name="Origen", institution="Banco")
    account_b = make_account(db, name="Destino", institution="Banco")
    db.commit()

    payload = {
        "account_id": account_a.id,
        "transaction_date": str(date.today()),
        "description": "Mi transferencia",
        "amount": 10000.0,
        "tx_type": "transfer",
        "currency": "ARS",
        "to_account_id": account_b.id,
    }
    response = client.post("/api/transactions", json=payload)
    transfer_id = response.json()["transfer_id"]

    all_txs = client.get("/api/transactions").json()["items"]
    legs = [tx for tx in all_txs if tx["transfer_id"] == transfer_id]
    account_ids = {tx["account_id"] for tx in legs}
    assert account_ids == {account_a.id, account_b.id}


def test_create_transfer_without_to_account_id_returns_422(client, db):
    """
    A transfer without a `to_account_id` must be rejected with HTTP 422.
    """
    account = make_account(db)
    db.commit()

    payload = {
        "account_id": account.id,
        "transaction_date": str(date.today()),
        "description": "Transferencia sin destino",
        "amount": 5000.0,
        "tx_type": "transfer",
        "currency": "ARS",
    }
    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 422


def test_create_transfer_both_legs_have_type_transfer(client, db):
    """
    Both transaction legs created by a transfer must have tx_type == 'transfer'.
    """
    account_a = make_account(db, name="A", institution="Banco")
    account_b = make_account(db, name="B", institution="Banco")
    db.commit()

    payload = {
        "account_id": account_a.id,
        "transaction_date": str(date.today()),
        "description": "Traspaso",
        "amount": 3000.0,
        "tx_type": "transfer",
        "currency": "ARS",
        "to_account_id": account_b.id,
    }
    response = client.post("/api/transactions", json=payload)
    transfer_id = response.json()["transfer_id"]

    all_txs = client.get("/api/transactions").json()["items"]
    legs = [tx for tx in all_txs if tx["transfer_id"] == transfer_id]
    assert all(tx["tx_type"] == "transfer" for tx in legs)


# ---------------------------------------------------------------------------
# DELETE /api/transactions/{id}
# ---------------------------------------------------------------------------


def test_delete_regular_transaction_returns_204(client, db):
    """
    DELETE on a non-transfer transaction must return HTTP 204 and remove the row.
    """
    account = make_account(db)
    tx = make_transaction(db, account_id=account.id, transaction_date=date.today(), description="A BORRAR", amount=100.0)
    db.commit()

    response = client.delete(f"/api/transactions/{tx.id}")
    assert response.status_code == 204

    get_response = client.get(f"/api/transactions/{tx.id}")
    assert get_response.status_code == 404


def test_delete_transfer_removes_both_legs(client, db):
    """
    Deleting one leg of a transfer must cascade and remove BOTH transaction rows
    that share the same transfer_id.
    """
    account_a = make_account(db, name="A", institution="Banco")
    account_b = make_account(db, name="B", institution="Banco")
    db.commit()

    payload = {
        "account_id": account_a.id,
        "transaction_date": str(date.today()),
        "description": "Transferencia",
        "amount": 7500.0,
        "tx_type": "transfer",
        "currency": "ARS",
        "to_account_id": account_b.id,
    }
    create_response = client.post("/api/transactions", json=payload)
    tx_id = create_response.json()["id"]

    # Verify two rows exist
    all_txs = client.get("/api/transactions").json()
    assert all_txs["total"] == 2

    # Delete one leg
    response = client.delete(f"/api/transactions/{tx_id}")
    assert response.status_code == 204

    # Both must be gone
    remaining = client.get("/api/transactions").json()
    assert remaining["total"] == 0


def test_delete_nonexistent_transaction_returns_404(client):
    """
    Attempting to delete a transaction that does not exist must return HTTP 404.
    """
    response = client.delete("/api/transactions/99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/transactions — list with filters
# ---------------------------------------------------------------------------


def test_list_transactions_returns_all_by_default(client, db):
    """
    GET /api/transactions without filters must return all transactions with
    total, page, page_size, and pages metadata.
    """
    account = make_account(db)
    make_transaction(db, account_id=account.id, transaction_date=date.today(), description="TX 1", amount=100.0)
    make_transaction(db, account_id=account.id, transaction_date=date.today(), description="TX 2", amount=200.0)
    db.commit()

    response = client.get("/api/transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data


def test_list_transactions_filters_by_account_id(client, db):
    """
    The `account_id` query parameter must restrict results to that account only.
    """
    account_a = make_account(db, name="A", institution="Banco")
    account_b = make_account(db, name="B", institution="Banco")
    make_transaction(db, account_id=account_a.id, transaction_date=date.today(), description="TX A", amount=100.0)
    make_transaction(db, account_id=account_b.id, transaction_date=date.today(), description="TX B", amount=200.0)
    db.commit()

    response = client.get(f"/api/transactions?account_id={account_a.id}")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["account_id"] == account_a.id


def test_list_transactions_filters_by_tx_type(client, db):
    """
    The `tx_type` query parameter must restrict results to the specified type.
    """
    account = make_account(db)
    make_transaction(db, account_id=account.id, transaction_date=date.today(), description="COMPRA", amount=500.0, tx_type="debit")
    make_transaction(db, account_id=account.id, transaction_date=date.today(), description="SUELDO", amount=100000.0, tx_type="credit")
    db.commit()

    debit_response = client.get("/api/transactions?tx_type=debit")
    credit_response = client.get("/api/transactions?tx_type=credit")

    assert debit_response.json()["total"] == 1
    assert credit_response.json()["total"] == 1
    assert debit_response.json()["items"][0]["tx_type"] == "debit"
    assert credit_response.json()["items"][0]["tx_type"] == "credit"


def test_list_transactions_paginates_correctly(client, db):
    """
    The `page` and `page_size` parameters must control which records are returned.
    Given 5 transactions and page_size=2:
      - page 1 → 2 items
      - page 2 → 2 items
      - page 3 → 1 item
      - total is always 5
      - pages == 3
    """
    account = make_account(db)
    for i in range(5):
        make_transaction(
            db,
            account_id=account.id,
            transaction_date=date.today(),
            description=f"COMPRA {i}",
            amount=float(100 + i),
        )
    db.commit()

    page1 = client.get("/api/transactions?page=1&page_size=2").json()
    page2 = client.get("/api/transactions?page=2&page_size=2").json()
    page3 = client.get("/api/transactions?page=3&page_size=2").json()

    assert page1["total"] == 5
    assert page1["pages"] == 3
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert len(page3["items"]) == 1


def test_list_transactions_pagination_items_are_non_overlapping(client, db):
    """
    Items on consecutive pages must not overlap (each tx appears exactly once).
    """
    account = make_account(db)
    for i in range(4):
        make_transaction(
            db,
            account_id=account.id,
            transaction_date=date.today(),
            description=f"COMPRA {i}",
            amount=float(100 + i),
        )
    db.commit()

    page1_ids = {tx["id"] for tx in client.get("/api/transactions?page=1&page_size=2").json()["items"]}
    page2_ids = {tx["id"] for tx in client.get("/api/transactions?page=2&page_size=2").json()["items"]}

    assert page1_ids.isdisjoint(page2_ids), "Pages must not overlap"


def test_list_transactions_filters_by_date_range(client, db):
    """
    `date_from` and `date_to` must filter transactions to the specified window.
    """
    account = make_account(db)
    today = date.today()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)

    make_transaction(db, account_id=account.id, transaction_date=today, description="HOY", amount=100.0)
    make_transaction(db, account_id=account.id, transaction_date=yesterday, description="AYER", amount=200.0)
    make_transaction(db, account_id=account.id, transaction_date=last_week, description="SEMANA PASADA", amount=300.0)
    db.commit()

    response = client.get(f"/api/transactions?date_from={yesterday}&date_to={today}")
    data = response.json()
    assert data["total"] == 2
    descriptions = {tx["description"] for tx in data["items"]}
    assert "HOY" in descriptions
    assert "AYER" in descriptions
    assert "SEMANA PASADA" not in descriptions


def test_list_transactions_empty_when_no_match(client, db):
    """
    If no transactions match the filter, the response must have total=0 and
    an empty items list.
    """
    account = make_account(db)
    make_transaction(db, account_id=account.id, transaction_date=date.today(), description="COMPRA", amount=100.0, tx_type="debit")
    db.commit()

    response = client.get("/api/transactions?tx_type=credit")
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# PUT /api/transactions/{id}
# ---------------------------------------------------------------------------


def test_update_transaction_description(client, db):
    """
    PUT with a new `description` must persist the change, update
    `description_normalized` accordingly, and return the updated record.
    """
    account = make_account(db)
    tx = make_transaction(db, account_id=account.id, transaction_date=date.today(), description="DESCRIPCION VIEJA", amount=500.0)
    db.commit()

    response = client.put(
        f"/api/transactions/{tx.id}",
        json={"description": "descripcion nueva"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "descripcion nueva"
    assert data["description_normalized"] == "DESCRIPCION NUEVA"


def test_update_transaction_amount(client, db):
    """
    PUT can change the transaction amount; the new value must be returned.
    """
    account = make_account(db)
    tx = make_transaction(db, account_id=account.id, transaction_date=date.today(), description="COMPRA", amount=100.0)
    db.commit()

    response = client.put(f"/api/transactions/{tx.id}", json={"amount": 999.99})
    assert response.status_code == 200
    assert response.json()["amount"] == 999.99


def test_update_transaction_category(client, db):
    """
    PUT can assign or change a category_id; the new value must be returned.
    """
    account = make_account(db)
    cat = make_category(db, name="Supermercados")
    tx = make_transaction(db, account_id=account.id, transaction_date=date.today(), description="COTO", amount=2000.0)
    db.commit()

    response = client.put(f"/api/transactions/{tx.id}", json={"category_id": cat.id})
    assert response.status_code == 200
    assert response.json()["category_id"] == cat.id


def test_update_transaction_notes(client, db):
    """
    PUT can set an optional notes field; the value must be persisted and returned.
    """
    account = make_account(db)
    tx = make_transaction(db, account_id=account.id, transaction_date=date.today(), description="COMPRA", amount=50.0)
    db.commit()

    response = client.put(f"/api/transactions/{tx.id}", json={"notes": "compra personal"})
    assert response.status_code == 200
    assert response.json()["notes"] == "compra personal"


def test_update_nonexistent_transaction_returns_404(client):
    """
    Attempting to update a transaction that does not exist must return HTTP 404.
    """
    response = client.put("/api/transactions/99999", json={"description": "No existe"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/transactions/{id}
# ---------------------------------------------------------------------------


def test_get_single_transaction_by_id(client, db):
    """
    GET /api/transactions/{id} must return the transaction identified by that id.
    """
    account = make_account(db)
    tx = make_transaction(db, account_id=account.id, transaction_date=date.today(), description="BUSCAR ESTA", amount=777.0)
    db.commit()

    response = client.get(f"/api/transactions/{tx.id}")
    assert response.status_code == 200
    assert response.json()["id"] == tx.id
    assert response.json()["description"] == "BUSCAR ESTA"


def test_get_nonexistent_transaction_returns_404(client):
    """
    Requesting a transaction that does not exist must return HTTP 404.
    """
    response = client.get("/api/transactions/99999")
    assert response.status_code == 404
