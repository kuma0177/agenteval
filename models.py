import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    INTAKE = "INTAKE"
    PAID = "PAID"
    SUBMITTED = "SUBMITTED"
    EVALUATING = "EVALUATING"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"


class EvalStatus(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=new_uuid)
    company_name = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    agent_description = Column(Text, nullable=False)
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.INTAKE)
    access_token = Column(String, unique=True, nullable=False, default=new_uuid)
    stripe_session = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    report_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    traces = relationship("Trace", back_populates="job")


class Trace(Base):
    __tablename__ = "traces"

    id = Column(String, primary_key=True, default=new_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    raw_json = Column(Text, nullable=False)
    turn_count = Column(Integer)
    outcome = Column(String, nullable=False)
    eval_status = Column(SAEnum(EvalStatus), nullable=False, default=EvalStatus.PENDING)
    llm_verdict = Column(String, nullable=True)
    llm_reasoning = Column(Text, nullable=True)
    llm_score = Column(Float, nullable=True)
    # v7 dimension scoring
    llm_score_overall = Column(Float, nullable=True)
    score_task_completion = Column(Float, nullable=True)
    score_tool_selection = Column(Float, nullable=True)
    score_reasoning = Column(Float, nullable=True)
    score_policy_compliance = Column(Float, nullable=True)
    score_hallucination_risk = Column(Float, nullable=True)
    dim_notes = Column(Text, nullable=True)
    failure_category = Column(String, nullable=True)
    failure_detail = Column(Text, nullable=True)
    human_verdict = Column(String, nullable=True)
    human_notes = Column(Text, nullable=True)
    reviewer_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="traces")
    reviewer_tokens = relationship("ReviewerToken", back_populates="trace")


class ReviewerToken(Base):
    __tablename__ = "reviewer_tokens"

    id = Column(String, primary_key=True, default=new_uuid)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, default=new_uuid)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    trace = relationship("Trace", back_populates="reviewer_tokens")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String)
    email = Column(String)
    company = Column(String)
    agent_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewerProfile(Base):
    __tablename__ = "reviewer_profiles"

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    domain_expertise = Column(String, nullable=False)
    years_experience = Column(Integer, nullable=True)
    linkedin_url = Column(String, nullable=True)
    hourly_rate_usd = Column(Integer, nullable=True)
    availability = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    status = Column(String, default="PENDING")
    rating = Column(Float, nullable=True)
    completed_reviews = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
