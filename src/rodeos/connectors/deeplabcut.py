import pandas as pd
from datetime import datetime
from typing import List, Optional
from rodeos.schemas.observation import Observation, DataClass, Provenance


class DeepLabCutConnector:
    """
    Connector to parse and ingest multi-animal or single-animal tracking exports
    from DeepLabCut (CSV format) into RodeOS standardized Observation models.
    """

    def __init__(self, software_version: str = "2.3.x"):
        self.software_version = software_version

    def parse_tracking_csv(
        self,
        file_path: str,
        study_id: str,
        animal_id: str,
        treatment_group: str,
        clock_source: str = "system_clock"
    ) -> List[Observation]:
        """
        Parses a standard DeepLabCut output CSV file and converts each frame's
        bodypart coordinates into standardized Observation instances.
        """
        # Read CSV, typically DeepLabCut exports have multi-level headers or standard 2-row headers
        # Row 0: bodyparts (e.g., snout, tailbase)
        # Row 1: coords (x, y, likelihood)
        df = pd.read_csv(file_path, header=[0, 1])

        observations: List[Observation] = []
        timestamp_now = datetime.utcnow()

        # Iterate through rows (frames)
        for frame_idx, row in df.iterrows():
            # Extract distinct bodyparts dynamically from column multi-index
            bodyparts = df.columns.levels[0].unique()

            for bp in bodyparts:
                try:
                    x_val = float(row[(bp, 'x')])
                    y_val = float(row[(bp, 'y')])
                    likelihood = float(row[(bp, 'likelihood')])
                except (KeyError, ValueError):
                    continue

                # Create position observation for X
                obs_x = Observation(
                    schema_version="1.0.0",
                    animal_id=animal_id,
                    study_id=study_id,
                    treatment_group=treatment_group,
                    timestamp=timestamp_now,
                    clock_source=clock_source,
                    name=f"{bp}_x",
                    value=x_val,
                    unit="pixels",
                    data_class=DataClass.AI_INFERRED,
                    provenance=Provenance(
                        source_instrument="DeepLabCut",
                        software_version=self.software_version,
                        analysis_method="markerless_pose_estimation",
                        model_name="ResNet-50 / DeeperCut",
                        model_version=self.software_version,
                        confidence=likelihood
                    )
                )
                observations.append(obs_x)

                # Create position observation for Y
                obs_y = Observation(
                    schema_version="1.0.0",
                    animal_id=animal_id,
                    study_id=study_id,
                    treatment_group=treatment_group,
                    timestamp=timestamp_now,
                    clock_source=clock_source,
                    name=f"{bp}_y",
                    value=y_val,
                    unit="pixels",
                    data_class=DataClass.AI_INFERRED,
                    provenance=Provenance(
                        source_instrument="DeepLabCut",
                        software_version=self.software_version,
                        analysis_method="markerless_pose_estimation",
                        model_name="ResNet-50 / DeeperCut",
                        model_version=self.software_version,
                        confidence=likelihood
                    )
                )
                observations.append(obs_y)

        return observations