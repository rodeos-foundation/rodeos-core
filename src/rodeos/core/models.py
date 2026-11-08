from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Enum as SQLEnum, JSON, String, Text
from sqlalchemy.orm import declarative_base
from rodeos.schemas.observation import DataClass

Base = declarative_base()


class ObservationModel(Base):
    __tablename__ = "observations"

    id = Column(String(36), primary_key=True, index=True)
    schema_version = Column(String(20), nullable=False)
    animal_id = Column(String(50), index=True, nullable=False)
    study_id = Column(String(50), index=True, nullable=False)
    treatment_group = Column(String(50), nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    clock_source = Column(String(100), nullable=False)
    name = Column(String(100), index=True, nullable=False)
    value = Column(JSON, nullable=False)  # Supports float or list of floats
    unit = Column(String(30), nullable=False)
    data_class = Column(SQLEnum(DataClass), nullable=False)
    provenance = Column(JSON, nullable=False)  # Stores Provenance model metadata
    simulation_run_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)