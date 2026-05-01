"""
Tests for app/routers/accounts.py

Documents the HTTP API for accounts via FastAPI TestClient.

The `client` fixture from conftest overrides `get_db` with an in-memory SQLite
session, so every test runs in full isolation against a real (but ephemeral) DB.

Accounts API surface:
  POST   /api/accounts           — create account (201)
  GET    /api/accounts           — list active accounts
  GET    /api/accounts/{id}      — get single account
  PUT    /api/accounts/{id}      — update fields
  DELETE /api/accounts/{id}      — soft-delete (is_active = False)
"""

from tests.conftest import make_account


# ---------------------------------------------------------------------------
# POST /api/accounts
# ---------------------------------------------------------------------------


def test_create_account_returns_201(client):
    """
    A well-formed POST body must create an account and return HTTP 201 with the
    persisted account data (id, timestamps, defaults).
    """
    response = client.post(
        "/api/accounts",
        json={"name": "Cuenta Corriente", "institution": "Banco Galicia"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Cuenta Corriente"
    assert data["institution"] == "Banco Galicia"
    assert data["currency"] == "ARS"           # default
    assert data["account_type"] == "checking"  # default
    assert data["is_active"] is True           # default
    assert "created_at" in data
    assert "updated_at" in data


def test_create_account_with_all_fields(client):
    """
    All optional fields (currency, account_type, current_balance, notes) must be
    stored and returned correctly.
    """
    response = client.post(
        "/api/accounts",
        json={
            "name": "Caja de Ahorro USD",
            "institution": "BBVA",
            "currency": "USD",
            "account_type": "savings",
            "current_balance": 1500.0,
            "notes": "Cuenta en dólares",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["currency"] == "USD"
    assert data["account_type"] == "savings"
    assert data["current_balance"] == 1500.0
    assert data["notes"] == "Cuenta en dólares"


def test_create_account_without_institution_returns_422(client):
    """
    The `institution` field is required.  Omitting it must return HTTP 422
    (Unprocessable Entity).
    """
    response = client.post("/api/accounts", json={"name": "Cuenta sin institución"})
    assert response.status_code == 422


def test_create_account_without_name_returns_422(client):
    """
    The `name` field is required.  Omitting it must return HTTP 422.
    """
    response = client.post("/api/accounts", json={"institution": "Banco"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/accounts
# ---------------------------------------------------------------------------


def test_list_accounts_returns_all_active_accounts(client, db):
    """
    GET /api/accounts must return all accounts whose is_active flag is True.
    """
    make_account(db, name="Cuenta A", institution="Banco A")
    make_account(db, name="Cuenta B", institution="Banco B")
    db.commit()

    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()
    names = [a["name"] for a in accounts]
    assert "Cuenta A" in names
    assert "Cuenta B" in names


def test_list_accounts_excludes_inactive(client, db):
    """
    Accounts with is_active=False must NOT appear in the list response.
    """
    active = make_account(db, name="Activa", institution="Banco")
    inactive = make_account(db, name="Inactiva", institution="Banco")
    inactive.is_active = False
    db.commit()

    response = client.get("/api/accounts")
    assert response.status_code == 200
    names = [a["name"] for a in response.json()]
    assert "Activa" in names
    assert "Inactiva" not in names


def test_list_accounts_empty_when_no_accounts(client):
    """
    With no accounts in the DB, the endpoint must return an empty list.
    """
    response = client.get("/api/accounts")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# PUT /api/accounts/{id}
# ---------------------------------------------------------------------------


def test_update_account_name(client, db):
    """
    PUT with a new `name` must persist the change and return the updated account.
    """
    account = make_account(db, name="Nombre Viejo", institution="Banco")
    db.commit()

    response = client.put(
        f"/api/accounts/{account.id}",
        json={"name": "Nombre Nuevo"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Nombre Nuevo"


def test_update_account_multiple_fields(client, db):
    """
    PUT can update several fields in a single request; all changes must be reflected.
    """
    account = make_account(db, name="Original", institution="Banco Viejo")
    db.commit()

    response = client.put(
        f"/api/accounts/{account.id}",
        json={"name": "Nuevo nombre", "institution": "Banco Nuevo", "current_balance": 99999.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Nuevo nombre"
    assert data["institution"] == "Banco Nuevo"
    assert data["current_balance"] == 99999.0


def test_update_nonexistent_account_returns_404(client):
    """
    Attempting to update an account that does not exist must return HTTP 404.
    """
    response = client.put("/api/accounts/99999", json={"name": "No existe"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/accounts/{id}
# ---------------------------------------------------------------------------


def test_delete_account_soft_deletes(client, db):
    """
    DELETE sets is_active=False (soft delete) and returns HTTP 204.
    The account must not appear in the list anymore, but it still exists in the DB.
    """
    account = make_account(db, name="Para Borrar", institution="Banco")
    db.commit()

    response = client.delete(f"/api/accounts/{account.id}")
    assert response.status_code == 204

    # Must not appear in list
    list_response = client.get("/api/accounts")
    names = [a["name"] for a in list_response.json()]
    assert "Para Borrar" not in names


def test_delete_account_returns_404_for_missing(client):
    """
    Attempting to delete a non-existent account must return HTTP 404.
    """
    response = client.delete("/api/accounts/99999")
    assert response.status_code == 404


def test_delete_then_recreate_different_account(client, db):
    """
    After soft-deleting an account, a new account with the same name can be
    created without conflict (soft-delete does not enforce name uniqueness).
    """
    account = make_account(db, name="Mi Cuenta", institution="Banco")
    db.commit()

    client.delete(f"/api/accounts/{account.id}")

    # Create a new one with the same name
    response = client.post(
        "/api/accounts",
        json={"name": "Mi Cuenta", "institution": "Banco"},
    )
    assert response.status_code == 201
    assert response.json()["is_active"] is True
