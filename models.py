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
    client_password_hash = Column(String, nullable=True)
    stripe_session = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    report_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    agent_profile_id = Column(String, nullable=True)

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
    llm_score_overall = Column(Float, nullable=True)
    llm_reasoning = Column(Text, nullable=True)
    failure_category = Column(String, nullable=True)
    failure_detail = Column(Text, nullable=True)
    # v7 dimension scores (legacy)
    llm_score = Column(Float, nullable=True)
    score_task_completion = Column(Float, nullable=True)
    score_tool_selection = Column(Float, nullable=True)
    score_reasoning = Column(Float, nullable=True)
    score_policy_compliance = Column(Float, nullable=True)
    score_hallucination_risk = Column(Float, nullable=True)
    # v9 dimension scores
    score_task_performance = Column(Float, nullable=True)
    score_reasoning_autonomy = Column(Float, nullable=True)
    score_operational_reliability = Column(Float, nullable=True)
    score_user_experience = Column(Float, nullable=True)
    score_ethics_safety = Column(Float, nullable=True)
    score_efficiency = Column(Float, nullable=True)
    dim_notes = Column(Text, nullable=True)
    human_verdict = Column(String, nullable=True)
    human_notes = Column(Text, nullable=True)
    reviewer_id = Column(String, nullable=True)
    reviewer_token = Column(String, nullable=True)
    client_comment = Column(Text, nullable=True)
    client_flagged = Column(Integer, default=0)
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
    status = Column(String, default="APPLIED")
    domain_scores = Column(Text, nullable=True)
    quiz_token = Column(String, nullable=True)
    quiz_score = Column(Float, nullable=True)
    quiz_submitted_at = Column(DateTime, nullable=True)
    trial_token = Column(String, nullable=True)
    trial_agreement_rate = Column(Float, nullable=True)
    nda_signed_at = Column(DateTime, nullable=True)
    nda_ip_address = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    completed_reviews = Column(Integer, default=0)
    total_earnings_usd = Column(Float, default=0)
    stripe_connect_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    quizzes = relationship("ReviewerQuiz", back_populates="reviewer")


class ReviewerQuiz(Base):
    __tablename__ = "reviewer_quizzes"

    id = Column(String, primary_key=True, default=new_uuid)
    reviewer_id = Column(String, ForeignKey("reviewer_profiles.id"), nullable=False)
    domain = Column(String, nullable=False)
    questions = Column(Text, nullable=False)
    answers = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    reviewer = relationship("ReviewerProfile", back_populates="quizzes")


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(String, primary_key=True, default=new_uuid)
    company_name = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    agent_description = Column(Text, nullable=True)
    is_public = Column(Integer, default=0)
    overall_avg = Column(Float, nullable=True)
    task_performance_avg = Column(Float, nullable=True)
    reasoning_autonomy_avg = Column(Float, nullable=True)
    operational_reliability_avg = Column(Float, nullable=True)
    user_experience_avg = Column(Float, nullable=True)
    ethics_safety_avg = Column(Float, nullable=True)
    efficiency_avg = Column(Float, nullable=True)
    audit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)


class EmailLog(Base):
    __tablename__ = "email_log"

    id = Column(String, primary_key=True, default=new_uuid)
    recipient_email = Column(String, nullable=False)
    email_type = Column(String, nullable=False)
    job_id = Column(String, nullable=True)
    reviewer_id = Column(String, nullable=True)
    resend_message_id = Column(String, nullable=True)
    status = Column(String, default="SENT")
    sent_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
