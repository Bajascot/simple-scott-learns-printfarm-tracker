from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import MaterialEnum, Spool

router = APIRouter(prefix="/spools", tags=["spools"])


class SpoolCreate(BaseModel):
    brand: str
    material: MaterialEnum
    color: str
    weight_total_g: float
    weight_remaining_g: float
    cost_total: float
    purchase_date: Optional[date] = None
    amazon_order_id: Optional[str] = None
    notes: Optional[str] = None


class SpoolUpdate(BaseModel):
    brand: Optional[str] = None
    material: Optional[MaterialEnum] = None
    color: Optional[str] = None
    weight_total_g: Optional[float] = None
    weight_remaining_g: Optional[float] = None
    cost_total: Optional[float] = None
    purchase_date: Optional[date] = None
    amazon_order_id: Optional[str] = None
    notes: Optional[str] = None


class SpoolResponse(BaseModel):
    id: int
    brand: str
    material: MaterialEnum
    color: str
    weight_total_g: float
    weight_remaining_g: float
    cost_total: float
    purchase_date: Optional[date]
    amazon_order_id: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[SpoolResponse])
def list_spools(db: Session = Depends(get_db)):
    return db.query(Spool).all()


@router.post("/", response_model=SpoolResponse, status_code=status.HTTP_201_CREATED)
def create_spool(data: SpoolCreate, db: Session = Depends(get_db)):
    spool = Spool(**data.model_dump())
    db.add(spool)
    db.commit()
    db.refresh(spool)
    return spool


@router.get("/{spool_id}", response_model=SpoolResponse)
def get_spool(spool_id: int, db: Session = Depends(get_db)):
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    return spool


@router.patch("/{spool_id}", response_model=SpoolResponse)
def update_spool(spool_id: int, data: SpoolUpdate, db: Session = Depends(get_db)):
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(spool, field, value)
    db.commit()
    db.refresh(spool)
    return spool


@router.delete("/{spool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spool(spool_id: int, db: Session = Depends(get_db)):
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    db.delete(spool)
    db.commit()
