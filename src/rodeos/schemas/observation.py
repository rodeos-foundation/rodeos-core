from datetime import datetime
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class DataClass(str, Enum):
    RAW = "raw"
    PROCESSED = "processed"
    AI_INFERRED = "ai_inferred"
    SYNTHETIC = "synthetic"


class Provenance(BaseModel):
    source_instrument: str
    software_version: str
    analysis_method: str
    upstream_ids: List[str] = Field(default_factory=list)
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[float] = None


class Observation(BaseModel):
    schema_version: str
    animal_id: str
    study_id: str
    treatment_group: str
    timestamp: datetime
    clock_source: str
    name: str  # For example, GaitVelocity
    value: Union[float, List[float]]
    unit: str
    data_class: DataClass
    provenance: Provenance
    simulation_run_id: Optional[str] = None  # Required when data_class is SYNTHETIC

    @model_validator(mode="after")
    def validate_observation_rules(self) -> "Observation":
        if self.data_class == DataClass.AI_INFERRED:
            if not self.provenance.model_name or not self.provenance.model_version or self.provenance.confidence is None:
                raise ValueError("AI_INFERRED observations require model_name, model_version, and confidence.")
        
        if self.data_class == DataClass.SYNTHETIC:
            if not self.simulation_run_id:
                raise ValueError("SYNTHETIC observations require a simulation_run_id.")
                
        return self