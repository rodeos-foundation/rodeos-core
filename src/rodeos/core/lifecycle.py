from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class StudyState(str, Enum):
    DESIGNED = "Designed"
    APPROVED = "Approved"
    RUNNING = "Running"
    PAUSED = "Paused"
    INTERRUPTED = "Interrupted"
    COMPLETED = "Completed"
    REVIEWED = "Reviewed"


class LifecycleTransition(BaseModel):
    study_id: str
    from_state: Optional[StudyState]
    to_state: StudyState
    actor: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None


class LifecycleManager:
    def __init__(self):
        self.audit_log: List[LifecycleTransition] = []
        self.study_states: dict[str, StudyState] = {}

    def transition(self, study_id: str, target_state: StudyState, actor: str, reason: Optional[str] = None) -> StudyState:
        current_state = self.study_states.get(study_id)
        if current_state is None and target_state != StudyState.DESIGNED:
            raise ValueError("New studies must start in the 'Designed' state.")
            
        transition_record = LifecycleTransition(
            study_id=study_id,
            from_state=current_state,
            to_state=target_state,
            actor=actor,
            reason=reason
        )
        self.audit_log.append(transition_record)
        self.study_states[study_id] = target_state
        return target_state