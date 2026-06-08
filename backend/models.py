from datetime import datetime, date
from enum import Enum

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db import Base


class MaterialEnum(str, Enum):
    PLA = "PLA"
    PETG = "PETG"
    ABS = "ABS"
    TPU = "TPU"
    ASA = "ASA"
    OTHER = "Other"


class JobStatusEnum(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Printer(Base):
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    model = Column(String, nullable=False)
    moonraker_url = Column(String, nullable=False)
    govee_device_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("PrintJob", back_populates="printer")


class Spool(Base):
    __tablename__ = "spools"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False)
    material = Column(SAEnum(MaterialEnum), nullable=False)
    color = Column(String, nullable=False)
    weight_total_g = Column(Float, nullable=False)
    weight_remaining_g = Column(Float, nullable=False)
    cost_total = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=True)
    amazon_order_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("PrintJob", back_populates="spool")
    purchases = relationship("Purchase", back_populates="linked_spool")


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    printer_id = Column(Integer, ForeignKey("printers.id"), nullable=False)
    spool_id = Column(Integer, ForeignKey("spools.id"), nullable=True)
    gcode_filename = Column(String, nullable=True)
    status = Column(SAEnum(JobStatusEnum), nullable=False, default=JobStatusEnum.RUNNING)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    filament_used_g = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    filament_cost = Column(Float, nullable=True)
    energy_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    notes = Column(String, nullable=True)

    printer = relationship("Printer", back_populates="jobs")
    spool = relationship("Spool", back_populates="jobs")


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (
        UniqueConstraint("amazon_order_id", "asin", name="uq_purchase_order_asin"),
    )

    id = Column(Integer, primary_key=True, index=True)
    amazon_order_id = Column(String, nullable=True, index=True)
    asin = Column(String, nullable=True)
    item_name = Column(String, nullable=False)
    filament_weight_g = Column(Float, nullable=True)
    cost = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=False)
    linked_spool_id = Column(Integer, ForeignKey("spools.id"), nullable=True)

    linked_spool = relationship("Spool", back_populates="purchases")


class EnergyRate(Base):
    __tablename__ = "energy_rates"

    id = Column(Integer, primary_key=True, index=True)
    rate_per_kwh = Column(Float, nullable=False)
    effective_from = Column(Date, nullable=False)
    label = Column(String, nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
