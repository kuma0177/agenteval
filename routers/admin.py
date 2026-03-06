import secrets
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, get_db
from models import EvalStatus, Job, JobStatus, Lead, ReviewerToken, Trace

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

STATUS_ORDER = ["INTAKE", "PAID", "SUBMITTED", "EVALUATING", "REVIEW", "COMPLETE"]


# ── Auth ──────────────────────────────────────────────────────────────────────

def _auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    ok_user = secrets.compare_digest(credentials.username.encode(), b"admin")
    ok_pass = secrets.compare_digest(
        credentials.password.encode(),
        settings.OPERATOR_PASSWORD.encode(),
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


Auth = Annotated[HTTPBasicCredentials, Depends(_auth)]


def _redirect(url: str, msg: str, msg_type: str = "success") -> RedirectResponse:
    return RedirectResponse(
        f"{url}?msg={quote(msg)}&msg_type={msg_type}", status_code=303
    )


def _get_job(job_id: str, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Background task helper (own DB session) ───────────────────────────────────

def _run_evaluate_bg(job_id: str):
    from services.llm_judge import evaluate_job
    db = SessionLocal()
    try:
        evaluate_job(job_id, db)
    finally:
        db.close()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, auth: Auth, db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()

    paid_statuses = [
        JobStatus.PAID, JobStatus.SUBMITTED, JobStatus.EVALUATING,
        JobStatus.REVIEW, JobStatus.COMPLETE,
    ]
    total    = len(jobs)
    paid     = sum(1 for j in jobs if j.status == JobStatus.PAID)
    in_eval  = sum(1 for j in jobs if j.status == JobStatus.EVALUATING)
    complete = sum(1 for j in jobs if j.status == JobStatus.COMPLETE)
    revenue  = sum(1 for j in jobs if j.status in paid_statuses) * 3500

    trace_counts = {
        job.id: db.query(Trace).filter(Trace.job_id == job.id).count()
        for job in jobs
    }

    return templates.TemplateResponse("admin_dashboard.html", {
        "request":      request,
        "jobs":         jobs,
        "total":        total,
        "paid":         paid,
        "in_eval":      in_eval,
        "complete":     complete,
        "revenue":      revenue,
        "trace_counts": trace_counts,
        "config":       settings,
    })


# ── New job ───────────────────────────────────────────────────────────────────

@router.get("/new", response_class=HTMLResponse)
def admin_new_form(
    request: Request,
    auth: Auth,
    prefill: str = None,
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == prefill).first() if prefill else None
    return templates.TemplateResponse("admin_new.html", {
        "request": request,
        "lead":    lead,
        "config":  settings,
    })


@router.post("/new")
def admin_create_job(
    auth: Auth,
    company_name:      str = Form(...),
    contact_name:      str = Form(...),
    contact_email:     str = Form(...),
    agent_description: str = Form(...),
    audit_type:        str = Form("starter"),
    notes:             str = Form(""),
    db: Session = Depends(get_db),
):
    job = Job(
        company_name=company_name,
        contact_name=contact_name,
        contact_email=contact_email,
        agent_description=agent_description,
        notes=notes or None,
        status=JobStatus.INTAKE,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return RedirectResponse(f"/admin/job/{job.id}?created=true", status_code=303)


# ── Job detail ────────────────────────────────────────────────────────────────

@router.get("/job/{job_id}", response_class=HTMLResponse)
def admin_job_detail(
    job_id: str,
    request: Request,
    auth: Auth,
    msg: str = None,
    msg_type: str = "success",
    created: str = None,
    db: Session = Depends(get_db),
):
    job    = _get_job(job_id, db)
    traces = db.query(Trace).filter(Trace.job_id == job_id).all()

    needs_review_traces = [t for t in traces if t.eval_status == EvalStatus.NEEDS_REVIEW]

    reviewer_token_map = {}
    for t in needs_review_traces:
        rt = db.query(ReviewerToken).filter(
            ReviewerToken.trace_id == t.id,
            ReviewerToken.used == False,  # noqa: E712
        ).first()
        if rt:
            reviewer_token_map[t.id] = rt.token

    flash_msg  = msg or ("Job created successfully" if created == "true" else None)
    flash_type = msg_type if msg else "success"

    current_status_idx = STATUS_ORDER.index(job.status.value) if job.status.value in STATUS_ORDER else 0

    return templates.TemplateResponse("admin_job.html", {
        "request":             request,
        "job":                 job,
        "traces":              traces,
        "needs_review_traces": needs_review_traces,
        "reviewer_token_map":  reviewer_token_map,
        "flash_msg":           flash_msg,
        "flash_type":          flash_type,
        "status_order":        STATUS_ORDER,
        "current_status_idx":  current_status_idx,
        "config":              settings,
    })


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/job/{job_id}/send-intake")
def admin_send_intake(job_id: str, auth: Auth, db: Session = Depends(get_db)):
    from services.email_service import send_intake_email
    job = _get_job(job_id, db)
    ok  = send_intake_email(job)
    msg = "Intake email sent" if ok else "Failed to send email — check RESEND_API_KEY"
    return _redirect(f"/admin/job/{job_id}", msg, "success" if ok else "error")


@router.post("/job/{job_id}/evaluate")
def admin_evaluate(
    job_id: str,
    auth: Auth,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = _get_job(job_id, db)
    job.status = JobStatus.EVALUATING
    db.commit()
    background_tasks.add_task(_run_evaluate_bg, job_id)
    return _redirect(f"/admin/job/{job_id}", "Evaluation started — results will appear shortly")


@router.post("/job/{job_id}/send-reviewer/{trace_id}")
def admin_send_reviewer(
    job_id: str,
    trace_id: str,
    auth: Auth,
    reviewer_email: str = Form(...),
    db: Session = Depends(get_db),
):
    from services.email_service import send_reviewer_email
    trace = db.query(Trace).filter(Trace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404)

    rt = db.query(ReviewerToken).filter(
        ReviewerToken.trace_id == trace_id,
        ReviewerToken.used == False,  # noqa: E712
    ).first()
    if not rt:
        rt = ReviewerToken(trace_id=trace_id)
        db.add(rt)
        db.commit()
        db.refresh(rt)

    ok  = send_reviewer_email(reviewer_email, trace, rt.token)
    msg = f"Review email sent to {reviewer_email}" if ok else "Failed to send email"
    return _redirect(f"/admin/job/{job_id}", msg, "success" if ok else "error")


@router.post("/job/{job_id}/generate-report")
def admin_generate_report(job_id: str, auth: Auth, db: Session = Depends(get_db)):
    from services.pdf_generator import generate_report
    try:
        generate_report(job_id, db)
        job = _get_job(job_id, db)
        job.status = JobStatus.COMPLETE
        db.commit()
        return _redirect(f"/admin/job/{job_id}", "Report generated successfully")
    except Exception as exc:
        return _redirect(f"/admin/job/{job_id}", f"Report failed: {exc}", "error")


@router.post("/job/{job_id}/email-report")
def admin_email_report(job_id: str, auth: Auth, db: Session = Depends(get_db)):
    from services.email_service import send_report_ready_email
    job = _get_job(job_id, db)
    ok  = send_report_ready_email(job)
    msg = "Report email sent to client" if ok else "Failed to send email"
    return _redirect(f"/admin/job/{job_id}", msg, "success" if ok else "error")


@router.post("/job/{job_id}/mark-complete")
def admin_mark_complete(job_id: str, auth: Auth, db: Session = Depends(get_db)):
    job = _get_job(job_id, db)
    job.status = JobStatus.COMPLETE
    db.commit()
    return _redirect(f"/admin/job/{job_id}", "Job marked as complete")


@router.patch("/job/{job_id}/notes")
async def admin_update_notes(
    job_id: str,
    auth: Auth,
    request: Request,
    db: Session = Depends(get_db),
):
    body  = await request.json()
    notes = body.get("notes", "")
    job   = _get_job(job_id, db)
    job.notes = notes
    db.commit()
    return JSONResponse({"success": True})


# ── Leads ─────────────────────────────────────────────────────────────────────

@router.get("/leads", response_class=HTMLResponse)
def admin_leads(request: Request, auth: Auth, db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return templates.TemplateResponse("admin_leads.html", {
        "request": request,
        "leads":   leads,
        "config":  settings,
    })
