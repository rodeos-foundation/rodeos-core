from datetime import datetime
import uuid
from rodeos.core.database import SessionLocal, init_db
from rodeos.core.models import ObservationModel
from rodeos.connectors.deeplabcut import DeepLabCutConnector

def run_test():
    # Ensure database tables exist
    init_db()
    
    # 1. Parse the sample DeepLabCut export using your connector
    connector = DeepLabCutConnector()
    observations = connector.parse_tracking_csv(
        file_path="sample_dlc_output.csv",
        study_id="STUDY-001",
        animal_id="RODENT-042",
        treatment_group="Control"
    )
    
    print(f"Successfully parsed {len(observations)} observations from DeepLabCut output.")

    # 2. Persist observations into the database using SQLAlchemy session
    db = SessionLocal()
    try:
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
        
        db.commit()
        print("Successfully committed DeepLabCut observations to SQLite database (rodeos.db).")
        
    except Exception as e:
        db.rollback()
        print(f"Error committing to database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_test()