from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.instrument import Instrument
from app.schemas.instrument import InstrumentCreate, InstrumentRead, InstrumentUpdate
from app.services.instrument_pricer import refresh_prices

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


@router.get("", response_model=list[InstrumentRead])
def list_instruments(instrument_type: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Instrument)
    if instrument_type:
        q = q.filter(Instrument.instrument_type == instrument_type)
    return q.order_by(Instrument.ticker).all()


@router.get("/search", response_model=list[InstrumentRead])
def search_instruments(q: str, db: Session = Depends(get_db)):
    pattern = f"%{q}%"
    return (
        db.query(Instrument)
        .filter(
            (Instrument.ticker.ilike(pattern)) | (Instrument.name.ilike(pattern))
        )
        .limit(20)
        .all()
    )


@router.post("", response_model=InstrumentRead, status_code=201)
def create_instrument(data: InstrumentCreate, db: Session = Depends(get_db)):
    instrument = Instrument(**data.model_dump())
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    return instrument


@router.get("/{instrument_id}", response_model=InstrumentRead)
def get_instrument(instrument_id: int, db: Session = Depends(get_db)):
    inst = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return inst


@router.put("/{instrument_id}", response_model=InstrumentRead)
def update_instrument(
    instrument_id: int, data: InstrumentUpdate, db: Session = Depends(get_db)
):
    inst = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(inst, field, value)
    db.commit()
    db.refresh(inst)
    return inst


@router.delete("/{instrument_id}", status_code=204)
def delete_instrument(instrument_id: int, db: Session = Depends(get_db)):
    from app.models.holding import Holding

    inst = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")
    holdings_count = db.query(Holding).filter(Holding.instrument_id == instrument_id).count()
    if holdings_count > 0:
        raise HTTPException(status_code=400, detail="Instrument has active holdings")
    db.delete(inst)
    db.commit()


@router.post("/refresh-prices")
async def refresh_instrument_prices(db: Session = Depends(get_db)):
    updated = await refresh_prices(db)
    return {"updated": updated}
