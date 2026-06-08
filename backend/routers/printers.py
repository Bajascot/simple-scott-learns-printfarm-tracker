from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Printer

router = APIRouter(prefix="/printers", tags=["printers"])


class PrinterCreate(BaseModel):
    name: str
    model: str
    moonraker_url: str
    govee_device_id: Optional[str] = None
    notes: Optional[str] = None


class PrinterUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    moonraker_url: Optional[str] = None
    govee_device_id: Optional[str] = None
    notes: Optional[str] = None


class PrinterResponse(BaseModel):
    id: int
    name: str
    model: str
    moonraker_url: str
    govee_device_id: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[PrinterResponse])
def list_printers(db: Session = Depends(get_db)):
    return db.query(Printer).all()


@router.post("", response_model=PrinterResponse, status_code=status.HTTP_201_CREATED)
def create_printer(data: PrinterCreate, db: Session = Depends(get_db)):
    printer = Printer(**data.model_dump())
    db.add(printer)
    db.commit()
    db.refresh(printer)
    return printer


@router.get("/{printer_id}", response_model=PrinterResponse)
def get_printer(printer_id: int, db: Session = Depends(get_db)):
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return printer


@router.patch("/{printer_id}", response_model=PrinterResponse)
def update_printer(printer_id: int, data: PrinterUpdate, db: Session = Depends(get_db)):
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(printer, field, value)
    db.commit()
    db.refresh(printer)
    return printer


@router.delete("/{printer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_printer(printer_id: int, db: Session = Depends(get_db)):
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    db.delete(printer)
    db.commit()
