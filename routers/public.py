import math
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AgentProfile, Lead, Trace, Job, EvalStatus
from config import settings

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="templates")


# ── Lead schema for JSON POST ─────────────────────────────────────────────────

class LeadIn(BaseModel):
    email: str
    company: str = ""
    name: str = ""
    agent_description: str = ""


# ── Homepage ──────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "config": settings})


# ── Lead capture (JSON — called from homepage fetch()) ───────────────────────

@router.post("/leads", status_code=201)
def create_lead(lead: LeadIn, db: Session = Depends(get_db)):
    from services.email_service import send_sample_report_email, send_new_lead_alert
    db_lead = Lead(
        name=lead.name,
        email=lead.email,
        company=lead.company,
        agent_description=lead.agent_description,
    )
    db.add(db_lead)
    db.commit()
    send_sample_report_email(lead.email, lead.company or "")
    send_new_lead_alert(db_lead)
    return JSONResponse({"ok": True}, status_code=201)


# ── Agent scorecard index ─────────────────────────────────────────────────────

@router.get("/agents", response_class=HTMLResponse)
def agent_scorecard_index(request: Request, db: Session = Depends(get_db)):
    profiles = (
        db.query(AgentProfile)
        .filter(AgentProfile.is_public == 1)
        .order_by(AgentProfile.overall_avg.desc().nullslast())
        .all()
    )
    return templates.TemplateResponse("agent_scorecard.html", {
        "request": request,
        "profiles": profiles,
        "config": settings,
    })


# ── Agent profile detail ──────────────────────────────────────────────────────

_DIMS = [
    ("task_performance_avg",        "Task Performance",        "30%"),
    ("reasoning_autonomy_avg",      "Reasoning & Autonomy",    "20%"),
    ("operational_reliability_avg", "Operational Reliability", "15%"),
    ("user_experience_avg",         "User Experience & Trust", "15%"),
    ("ethics_safety_avg",           "Ethics & Safety",         "10%"),
    ("efficiency_avg",              "Efficiency",              "10%"),
]


def _radar_points(profile: AgentProfile, cx: int = 150, cy: int = 150, r: int = 110) -> tuple[str, list]:
    """Compute SVG polygon points + dot positions for radar chart."""
    vals = [
        profile.task_performance_avg,
        profile.reasoning_autonomy_avg,
        profile.operational_reliability_avg,
        profile.user_experience_avg,
        profile.ethics_safety_avg,
        profile.efficiency_avg,
    ]
    n = 6
    pts = []
    dots = []
    for i, v in enumerate(vals):
        angle = math.radians(i * 360 / n - 90)
        scale = (v if v is not None else 0.0)
        x = cx + r * scale * math.cos(angle)
        y = cy + r * scale * math.sin(angle)
        pts.append(f"{x:.1f},{y:.1f}")
        dots.append((round(x, 1), round(y, 1)))
    return " ".join(pts), dots


@router.get("/agents/{agent_profile_id}", response_class=HTMLResponse)
def agent_profile_detail(agent_profile_id: str, request: Request, db: Session = Depends(get_db)):
    profile = db.query(AgentProfile).filter(AgentProfile.id == agent_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    score_pct = int(profile.overall_avg * 100) if profile.overall_avg else 0
    if score_pct >= 75:
        score_color = "#1d8348"
    elif score_pct >= 50:
        score_color = "#d68910"
    else:
        score_color = "#b03a2e"

    radar_points, radar_dots = _radar_points(profile)

    # Build audit history from jobs linked to this profile
    jobs = (
        db.query(Job)
        .filter(Job.agent_profile_id == profile.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    audit_history = []
    for job in jobs:
        traces = db.query(Trace).filter(Trace.job_id == job.id).all()
        evaluated = [t for t in traces if t.eval_status in (EvalStatus.PASS, EvalStatus.FAIL)]
        pass_count = sum(1 for t in evaluated if t.eval_status == EvalStatus.PASS)
        pass_pct = int(pass_count / len(evaluated) * 100) if evaluated else 0
        audit_history.append({
            "company_name": job.company_name,
            "created_at":   job.created_at,
            "trace_count":  len(evaluated),
            "pass_pct":     pass_pct,
        })

    return templates.TemplateResponse("agent_profile.html", {
        "request":       request,
        "profile":       profile,
        "dims":          _DIMS,
        "score_pct":     score_pct,
        "score_color":   score_color,
        "radar_points":  radar_points,
        "radar_dots":    radar_dots,
        "audit_history": audit_history,
        "config":        settings,
    })
