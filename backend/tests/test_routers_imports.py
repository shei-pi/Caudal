# TODO: implement app/routers/imports.py
# Endpoints:
#   POST   /api/imports/upload          — multipart upload, returns ImportPreview
#   POST   /api/imports/{job_id}/rows   — save user edits to raw_preview
#   POST   /api/imports/{job_id}/confirm — create transactions from approved rows
#   DELETE /api/imports/{job_id}        — cancel job

import io
import json
from datetime import date
from unittest.mock import MagicMock, patch

from app.models.import_job import ImportJob
from app.ingestion.base import ParsedRow, ParseResult
from tests.conftest import make_account, make_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parsed_rows() -> list[ParsedRow]:
    return [
        ParsedRow(
            transaction_date=date(2025, 4, 1),
            description="CARREFOUR PALERMO",
            amount=3500.0,
            tx_type="debit",
        ),
        ParsedRow(
            transaction_date=date(2025, 4, 5),
            description="DEPOSITO SUELDO",
            amount=150000.0,
            tx_type="credit",
        ),
    ]


def _fake_pdf_file(filename: str = "estado_cuenta.pdf") -> tuple[str, bytes, str]:
    """Return (field_name, content, filename) for multipart upload."""
    return ("file", b"%PDF-1.4 fake pdf content", filename)


def _mock_parser(
    parsed_rows: list[ParsedRow],
    statement_total: float | None = None,
    total_kind: str | None = None,
) -> MagicMock:
    mock = MagicMock()
    mock.bank_name = "Galicia"
    mock.parse.return_value = ParseResult(
        rows=parsed_rows,
        statement_total=statement_total,
        total_kind=total_kind,
    )
    return mock


# ---------------------------------------------------------------------------
# POST /api/imports/upload
# ---------------------------------------------------------------------------


def test_upload_creates_import_job_in_db(client, db):
    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    job_id = data["job_id"]
    job = db.get(ImportJob, job_id)
    assert job is not None
    assert job.filename == "estado_cuenta.pdf"


def test_upload_returns_preview_with_parsed_rows(client, db):
    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["bank"] == "Galicia"
    assert isinstance(data["rows"], list)
    assert len(data["rows"]) == 2
    assert data["rows"][0]["description"] == "CARREFOUR PALERMO"
    assert data["rows"][0]["amount"] == 3500.0


def test_upload_detects_account_by_institution_name(client, db):
    account = make_account(db, name="Caja de Ahorro", institution="Banco Galicia")
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    mock_parser.bank_name = "Galicia"
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("galicia.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["detected_account_id"] == account.id


def test_upload_marks_rows_duplicate_when_fingerprint_exists(client, db):
    account = make_account(db, name="Caja de Ahorro", institution="Banco Galicia")
    make_transaction(
        db,
        account_id=account.id,
        transaction_date=date(2025, 4, 1),
        description="CARREFOUR PALERMO",
        amount=3500.0,
        tx_type="debit",
    )
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    mock_parser.bank_name = "Galicia"
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("galicia.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    assert response.status_code == 200
    data = response.json()
    preview_rows = data["rows"]
    duplicate_row = next(r for r in preview_rows if r["description"] == "CARREFOUR PALERMO")
    assert duplicate_row["is_duplicate"] is True
    assert duplicate_row["include"] is False


def test_upload_rejects_non_pdf_extension_returns_422(client, db):
    response = client.post(
        "/api/imports/upload",
        files={"file": ("extracto.txt", b"plain text content", "text/plain")},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/imports/{job_id}/rows
# ---------------------------------------------------------------------------


def test_update_rows_saves_edited_rows_to_raw_preview(client, db):
    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    edited_rows = [
        {
            "include": True,
            "transaction_date": "2025-04-01",
            "description": "CARREFOUR PALERMO EDITADO",
            "amount": 3500.0,
            "tx_type": "debit",
            "currency": "ARS",
            "category_id": None,
            "notes": "compra semanal",
            "is_duplicate": False,
        },
        {
            "include": False,
            "transaction_date": "2025-04-05",
            "description": "DEPOSITO SUELDO",
            "amount": 150000.0,
            "tx_type": "credit",
            "currency": "ARS",
            "category_id": None,
            "notes": None,
            "is_duplicate": False,
        },
    ]
    response = client.post(f"/api/imports/{job_id}/rows", json={"rows": edited_rows})
    assert response.status_code == 200

    db.expire_all()
    job = db.get(ImportJob, job_id)
    stored_rows = json.loads(job.raw_preview)
    assert stored_rows[0]["description"] == "CARREFOUR PALERMO EDITADO"
    assert stored_rows[0]["notes"] == "compra semanal"
    assert stored_rows[1]["include"] is False


# ---------------------------------------------------------------------------
# POST /api/imports/{job_id}/confirm
# ---------------------------------------------------------------------------


def test_confirm_creates_transactions_for_included_rows(client, db):
    account = make_account(db, name="CA Galicia", institution="Banco Galicia")
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    response = client.post(
        f"/api/imports/{job_id}/confirm",
        json={"account_id": account.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_rows"] == 2


def test_confirm_skips_excluded_rows(client, db):
    account = make_account(db, name="CA Galicia", institution="Banco Galicia")
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    preview_rows = upload_resp.json()["rows"]
    preview_rows[1]["include"] = False
    client.post(f"/api/imports/{job_id}/rows", json={"rows": preview_rows})

    response = client.post(
        f"/api/imports/{job_id}/confirm",
        json={"account_id": account.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_rows"] == 1


def test_confirm_deduplicates_on_confirm(client, db):
    account = make_account(db, name="CA Galicia", institution="Banco Galicia")
    make_transaction(
        db,
        account_id=account.id,
        transaction_date=date(2025, 4, 1),
        description="CARREFOUR PALERMO",
        amount=3500.0,
        tx_type="debit",
    )
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    preview_rows = upload_resp.json()["rows"]
    for row in preview_rows:
        row["include"] = True
    client.post(f"/api/imports/{job_id}/rows", json={"rows": preview_rows})

    response = client.post(
        f"/api/imports/{job_id}/confirm",
        json={"account_id": account.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_rows"] == 1
    assert data["duplicate_rows"] == 1


def test_confirm_sets_job_status_to_done(client, db):
    account = make_account(db, name="CA Galicia", institution="Banco Galicia")
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    client.post(f"/api/imports/{job_id}/confirm", json={"account_id": account.id})

    db.expire_all()
    job = db.get(ImportJob, job_id)
    assert job.status == "done"


def test_confirm_returns_imported_and_duplicate_counts(client, db):
    account = make_account(db, name="CA Galicia", institution="Banco Galicia")
    db.commit()

    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    response = client.post(
        f"/api/imports/{job_id}/confirm",
        json={"account_id": account.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "imported_rows" in data
    assert "duplicate_rows" in data


def test_confirm_404_for_unknown_job(client, db):
    response = client.post(
        "/api/imports/99999/confirm",
        json={"account_id": 1},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/imports/{job_id}
# ---------------------------------------------------------------------------


def test_cancel_sets_job_status_to_cancelled(client, db):
    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        upload_resp = client.post(
            "/api/imports/upload",
            files={"file": ("estado_cuenta.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    job_id = upload_resp.json()["job_id"]

    response = client.delete(f"/api/imports/{job_id}")
    assert response.status_code == 200

    db.expire_all()
    job = db.get(ImportJob, job_id)
    assert job.status == "cancelled"


# ---------------------------------------------------------------------------
# Validation in upload response
# ---------------------------------------------------------------------------


def test_upload_response_includes_validation_object(client, db):
    rows = _make_parsed_rows()
    # debit 3500, credit 150000 → for "balance_diff" total: 150000-3500=146500
    mock_parser = _mock_parser(rows, statement_total=146500.0, total_kind="balance_diff")
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("galicia.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    data = response.json()
    assert "validation" in data
    assert "is_valid" in data["validation"]
    assert "expected" in data["validation"]
    assert "actual" in data["validation"]
    assert "difference" in data["validation"]


def test_upload_validation_passes_when_totals_match(client, db):
    rows = _make_parsed_rows()  # debit 3500, credit 150000
    mock_parser = _mock_parser(rows, statement_total=146500.0, total_kind="balance_diff")
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("galicia.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    data = response.json()
    assert data["validation"]["is_valid"] is True
    assert data["validation"]["difference"] == 0


def test_upload_validation_fails_with_difference_when_totals_mismatch(client, db):
    rows = _make_parsed_rows()  # debit 3500, credit 150000 → diff would be 146500
    # Statement claims 100000 → off by 46500
    mock_parser = _mock_parser(rows, statement_total=100000.0, total_kind="balance_diff")
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("galicia.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    data = response.json()
    assert data["validation"]["is_valid"] is False
    assert data["validation"]["difference"] == 46500.0


def test_upload_validation_passes_when_no_total_declared(client, db):
    rows = _make_parsed_rows()
    mock_parser = _mock_parser(rows, statement_total=None, total_kind=None)
    with patch("app.routers.imports.detect_bank", return_value=mock_parser):
        response = client.post(
            "/api/imports/upload",
            files={"file": ("mp.csv", b"csv content", "text/csv")},
        )
    data = response.json()
    assert data["validation"]["is_valid"] is True
    assert data["validation"]["expected"] is None
