import hashlib
import io
import json
import tempfile
from datetime import date as date_type
from pathlib import Path

import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.ingestion.registry import detect_bank
from app.models.account import Account
from app.models.import_job import ImportJob
from app.models.transaction import Transaction
from app.services.import_validation import validate_import
from app.utils.text import normalize_description

router = APIRouter(prefix="/api/imports", tags=["imports"])

ALLOWED_EXTENSIONS = {".pdf", ".csv"}


class PreviewRow(BaseModel):
    include: bool
    transaction_date: str
    description: str
    amount: float
    tx_type: str
    currency: str = "ARS"
    category_id: int | None = None
    notes: str | None = None
    is_duplicate: bool = False


class UpdateRowsRequest(BaseModel):
    rows: list[PreviewRow]


class ConfirmRequest(BaseModel):
    account_id: int


def _make_fingerprint(tx_date, desc_norm: str, amount: float, account_id: int) -> str:
    raw = f"{tx_date}|{desc_norm}|{round(amount, 2)}|{account_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _detect_account(db: Session, bank_name: str) -> Account | None:
    bank_upper = bank_name.upper()
    accounts = db.query(Account).filter(Account.is_active == True).all()  # noqa: E712
    for account in accounts:
        if bank_upper in (account.institution or "").upper():
            return account
    return None


def _extract_text(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                if pdf.pages:
                    return pdf.pages[0].extract_text() or ""
        except Exception:
            pass
        return ""
    try:
        return file_bytes[:2000].decode("utf-8", errors="ignore")
    except Exception:
        return ""


@router.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Extensión '{ext}' no permitida")

    file_bytes = file.file.read()
    text = _extract_text(file_bytes, filename)
    parser = detect_bank(text)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        parse_result = parser.parse(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    job = ImportJob(
        filename=filename,
        file_type=ext.lstrip("."),
        bank=parser.bank_name,
        status="pending",
        total_rows=len(parse_result.rows),
    )
    db.add(job)
    db.flush()

    detected_account = _detect_account(db, parser.bank_name)
    detected_account_id = detected_account.id if detected_account else None

    preview_rows = []
    for row in parse_result.rows:
        is_duplicate = False
        if detected_account_id is not None:
            desc_norm = normalize_description(row.description)
            fingerprint = _make_fingerprint(
                row.transaction_date, desc_norm, row.amount, detected_account_id
            )
            is_duplicate = (
                db.query(Transaction)
                .filter(Transaction.hash_fingerprint == fingerprint)
                .first()
            ) is not None

        preview_rows.append({
            "include": not is_duplicate,
            "transaction_date": row.transaction_date.isoformat(),
            "description": row.description,
            "amount": row.amount,
            "tx_type": row.tx_type,
            "currency": row.currency,
            "category_id": None,
            "notes": row.notes,
            "is_duplicate": is_duplicate,
        })

    job.raw_preview = json.dumps(preview_rows)
    db.commit()
    db.refresh(job)

    validation = validate_import(parse_result)

    return {
        "job_id": job.id,
        "bank": parser.bank_name,
        "filename": filename,
        "detected_account_id": detected_account_id,
        "rows": preview_rows,
        "validation": {
            "is_valid": validation.is_valid,
            "expected": validation.expected,
            "actual": validation.actual,
            "difference": validation.difference,
            "message": validation.message,
        },
    }


@router.post("/{job_id}/rows")
def update_rows(job_id: int, body: UpdateRowsRequest, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    job.raw_preview = json.dumps([row.model_dump() for row in body.rows], default=str)
    db.commit()

    return {"ok": True}


@router.post("/{job_id}/confirm")
def confirm_import(job_id: int, body: ConfirmRequest, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    stored_rows = json.loads(job.raw_preview or "[]")
    imported = 0
    duplicates = 0

    for row in stored_rows:
        if not row.get("include", True):
            continue

        desc_norm = normalize_description(row["description"])
        tx_date_str = row["transaction_date"]
        amount = row["amount"]
        account_id = body.account_id

        fingerprint = _make_fingerprint(tx_date_str, desc_norm, amount, account_id)
        existing = (
            db.query(Transaction)
            .filter(Transaction.hash_fingerprint == fingerprint)
            .first()
        )
        if existing is not None:
            duplicates += 1
            continue

        tx = Transaction(
            account_id=account_id,
            transaction_date=date_type.fromisoformat(tx_date_str),
            description=row["description"],
            description_normalized=desc_norm,
            amount=amount,
            tx_type=row["tx_type"],
            currency=row.get("currency", "ARS"),
            category_id=row.get("category_id"),
            notes=row.get("notes"),
            hash_fingerprint=fingerprint,
            source="import",
            import_job_id=job.id,
        )
        db.add(tx)
        imported += 1

    job.status = "done"
    job.imported_rows = imported
    job.duplicate_rows = duplicates
    db.commit()

    return {"imported_rows": imported, "duplicate_rows": duplicates}


@router.delete("/{job_id}")
def cancel_import(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    job.status = "cancelled"
    db.commit()

    return {"ok": True}
