from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.integrations.amazon import import_from_csv
from backend.models import Purchase

router = APIRouter(prefix="/purchases", tags=["purchases"])


class PurchaseResponse(BaseModel):
    id: int
    amazon_order_id: Optional[str]
    asin: Optional[str]
    item_name: str
    filament_weight_g: Optional[float]
    cost: float
    purchase_date: date
    linked_spool_id: Optional[int]

    model_config = {"from_attributes": True}


@router.get("", response_model=List[PurchaseResponse])
def list_purchases(db: Session = Depends(get_db)):
    return db.query(Purchase).order_by(Purchase.purchase_date.desc()).all()


@router.post("/import/amazon-csv", status_code=status.HTTP_200_OK)
def import_amazon_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return import_from_csv(file.file, db)
