from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class StepResult(BaseModel):
    step_id: int
    is_successful: bool
    duration_seconds: int
    details: Dict[str, Any]

class Session(BaseModel):
    _id: str
    lesson_id: str
    child_id: str
    started_at: str
    completed_at: Optional[str]
    status: str
    total_score: Optional[int]
    step_results: List[StepResult]
    llm_analysis_status: str
    llm_analysis_report: Optional[str]