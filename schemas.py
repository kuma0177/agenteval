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
    llm_reasoning: Optional[str]
    llm_score: Optional[float]
    human_verdict: Optional[str]
    human_notes: Optional[str]
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
