from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.holding import Holding
from app.schemas.holding import HoldingCreate, HoldingRead, HoldingUpdate

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


@router.get("", response_model=list[HoldingRead])
def list_holdings(account_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Holding)
    if account_id:
        q = q.filter(Holding.account_id == account_id)
    return q.all()


@router.post("", response_model=HoldingRead, status_code=201)
def create_holding(data: HoldingCreate, db: Session = Depends(get_db)):
    holding = Holding(**data.model_dump())
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


@router.put("/{holding_id}", response_model=HoldingRead)
def update_holding(holding_id: int, data: HoldingUpdate, db: Session = Depends(get_db)):
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(holding, field, value)
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(holding)
    db.commit()
