"""Scorecard service.

Aggregates per-trace dimension scores into job-level and agent-profile-level summaries.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import AgentProfile, Job, Trace, EvalStatus


_DIMENSIONS = [
    "score_task_performance",
    "score_reasoning_autonomy",
    "score_operational_reliability",
    "score_user_experience",
    "score_ethics_safety",
    "score_efficiency",
]


def compute_job_scorecard(job_id: str, db: Session) -> dict:
    """Return aggregated dimension averages for all evaluated traces in a job."""
    traces = (
        db.query(Trace)
        .filter(
            Trace.job_id == job_id,
            Trace.eval_status.in_([EvalStatus.PASS, EvalStatus.FAIL]),
        )
        .all()
    )
    if not traces:
        return {}

    totals: dict[str, list[float]] = {d: [] for d in _DIMENSIONS}
    for trace in traces:
        for dim in _DIMENSIONS:
            val = getattr(trace, dim, None)
            if val is not None:
                totals[dim].append(val)

    averages = {
        dim: round(sum(vals) / len(vals), 2) if vals else None
        for dim, vals in totals.items()
    }

    scored = [v for v in averages.values() if v is not None]
    averages["overall_avg"] = round(sum(scored) / len(scored), 2) if scored else None
    averages["total_traces"] = len(traces)
    averages["pass_count"] = sum(1 for t in traces if t.eval_status == EvalStatus.PASS)
    return averages


def update_agent_profile(job: Job, db: Session) -> Optional[AgentProfile]:
    """Recompute and persist dimension averages on the linked AgentProfile (if any)."""
    if not job.agent_profile_id:
        return None

    profile = db.query(AgentProfile).filter(AgentProfile.id == job.agent_profile_id).first()
    if not profile:
        return None

    scorecard = compute_job_scorecard(job.id, db)
    if not scorecard:
        return profile

    dim_map = {
        "score_task_performance": "task_performance_avg",
        "score_reasoning_autonomy": "reasoning_autonomy_avg",
        "score_operational_reliability": "operational_reliability_avg",
        "score_user_experience": "user_experience_avg",
        "score_ethics_safety": "ethics_safety_avg",
        "score_efficiency": "efficiency_avg",
    }
    for score_col, avg_col in dim_map.items():
        setattr(profile, avg_col, scorecard.get(score_col))

    profile.overall_avg = scorecard.get("overall_avg")
    profile.audit_count = (profile.audit_count or 0) + 1
    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile
