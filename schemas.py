from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from models import JobStatus, EvalStatus


class LeadCreate(BaseModel):
    name: str
    email: str
    company: str
    agent_description: str


class LeadOut(BaseModel):
    id: str
    name: Optional[str]
    email: Optional[str]
    company: Optional[str]
    agent_description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    agent_description: str


class JobOut(BaseModel):
    id: str
    company_name: str
    contact_name: str
    contact_email: str
    agent_description: str
    status: JobStatus
    access_token: str
    stripe_session: Optional[str]
    created_at: datetime
    report_path: Optional[str]
    notes: Optional[str]
    last_viewed_at: Optional[datetime]
    agent_profile_id: Optional[str]

    class Config:
        from_attributes = True


class TraceCreate(BaseModel):
    raw_json: str
    turn_count: Optional[int] = None
    outcome: str


class TraceOut(BaseModel):
    id: str
    job_id: str
    turn_count: Optional[int]
    outcome: str
    eval_status: EvalStatus
    llm_verdict: Optional[str]
    llm_score_overall: Optional[float]
    llm_reasoning: Optional[str]
    failure_category: Optional[str]
    score_task_performance: Optional[float]
    score_reasoning_autonomy: Optional[float]
    score_operational_reliability: Optional[float]
    score_user_experience: Optional[float]
    score_ethics_safety: Optional[float]
    score_efficiency: Optional[float]
    human_verdict: Optional[str]
    human_notes: Optional[str]
    reviewer_id: Optional[str]
    client_comment: Optional[str]
    client_flagged: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewerTokenOut(BaseModel):
    id: str
    trace_id: str
    token: str
    used: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewerProfileOut(BaseModel):
    id: str
    name: str
    email: str
    domain_expertise: str
    years_experience: Optional[int]
    status: str
    rating: Optional[float]
    completed_reviews: int
    total_earnings_usd: float
    created_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True


class AgentProfileOut(BaseModel):
    id: str
    company_name: str
    agent_name: str
    agent_description: Optional[str]
    is_public: int
    overall_avg: Optional[float]
    task_performance_avg: Optional[float]
    reasoning_autonomy_avg: Optional[float]
    operational_reliability_avg: Optional[float]
    user_experience_avg: Optional[float]
    ethics_safety_avg: Optional[float]
    efficiency_avg: Optional[float]
    audit_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class EmailLogOut(BaseModel):
    id: str
    recipient_email: str
    email_type: str
    job_id: Optional[str]
    reviewer_id: Optional[str]
    status: str
    sent_at: datetime
    error_message: Optional[str]

    class Config:
        from_attributes = True
