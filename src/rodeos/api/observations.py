from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from rodeos.schemas.observation import Observation
from rodeos.core.database import get_db
from rodeos.core.models import ObservationModel

router = APIRouter(prefix="/api/v1/observations", tags=["observations"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_observations(observations: List[Observation], db: Session = Depends(get_db)):
    db_objects = []
    for obs in observations:
        db_obs = ObservationModel(
            id=str(uuid.uuid4()),
            schema_version=obs.schema_version,
            animal_id=obs.animal_id,
            study_id=obs.study_id,
            treatment_group=obs.treatment_group,
            timestamp=obs.timestamp,
            clock_source=obs.clock_source,
            name=obs.name,
            value=obs.value,
            unit=obs.unit,
            data_class=obs.data_class,
            provenance=obs.provenance.model_dump(),
            simulation_run_id=obs.simulation_run_id
        )
        db.add(db_obs)
        db_objects.append(db_obs)
    
    db.commit()
    return {"status": "success", "count": len(db_objects)}