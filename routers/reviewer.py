from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import ReviewerToken, Trace, Job, JobStatus, EvalStatus, ReviewerProfile
from config import settings
from services.email_service import send_email

router = APIRouter(tags=["reviewer"])
templates = Jinja2Templates(directory="templates")


# ── Apply ─────────────────────────────────────────────────────────────────────

@router.get("/reviewers/apply", response_class=HTMLResponse)
def reviewer_apply_form(request: Request):
    return templates.TemplateResponse("reviewer_apply.html", {
        "request": request, "config": settings,
    })


@router.post("/reviewers/apply")
async def reviewer_apply_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    from services.email_service import send_new_application_alert

    form = await request.form()
    name             = (form.get("name") or "").strip()
    email            = (form.get("email") or "").strip()
    domain_expertise = (form.get("domain_expertise") or "").strip()
    current_role     = (form.get("current_role") or "").strip()
    linkedin_url     = (form.get("linkedin_url") or "").strip() or None
    availability     = (form.get("availability") or "").strip() or None
    bio_raw          = (form.get("bio") or "").strip()
    bio              = f"Role: {current_role}\n\n{bio_raw}".strip() if current_role else bio_raw or None

    try:
        years_experience = int(form.get("years_experience") or 0)
    except (TypeError, ValueError):
        years_experience = None

    try:
        hourly_rate_usd = int(form.get("hourly_rate_usd") or 0) or None
    except (TypeError, ValueError):
        hourly_rate_usd = None

    if not name or not email or not domain_expertise:
        return JSONResponse({"ok": False, "error": "Name, email, and domain are required."}, status_code=400)

    existing = db.query(ReviewerProfile).filter(ReviewerProfile.email == email).first()
    if not existing:
        profile = ReviewerProfile(
            name=name,
            email=email,
            domain_expertise=domain_expertise,
            years_experience=years_experience,
            linkedin_url=linkedin_url,
            hourly_rate_usd=hourly_rate_usd,
            availability=availability,
            bio=bio,
            status="APPLIED",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        send_new_application_alert(profile)
    else:
        profile = existing

    return JSONResponse({"ok": True})


# ── Review (human verdict) ────────────────────────────────────────────────────

@router.get("/review/{token}", response_class=HTMLResponse)
def review_page(token: str, request: Request, db: Session = Depends(get_db)):
    reviewer_token = db.query(ReviewerToken).filter(ReviewerToken.token == token).first()
    if not reviewer_token:
        raise HTTPException(status_code=404, detail="Review link not found.")
    if reviewer_token.used:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;padding:48px;'>"
            "<h2>This link has already been used.</h2>"
            "<p>Each review link is single-use. Contact hello@agenteval.com if you need help.</p>"
            "</body></html>"
        )
    trace = db.query(Trace).filter(Trace.id == reviewer_token.trace_id).first()
    job   = db.query(Job).filter(Job.id == trace.job_id).first() if trace else None
    return templates.TemplateResponse("review.html", {
        "request": request,
        "trace": trace,
        "job": job,
        "reviewer_token": reviewer_token,
        "config": settings,
    })


@router.post("/review/{token}", response_class=HTMLResponse)
async def submit_review(token: str, request: Request, db: Session = Depends(get_db)):
    reviewer_token = db.query(ReviewerToken).filter(ReviewerToken.token == token).first()
    if not reviewer_token or reviewer_token.used:
        raise HTTPException(status_code=400, detail="Invalid or already-used review token.")

    form    = await request.form()
    verdict = form.get("verdict", "").upper()
    notes   = form.get("notes", "")

    if verdict not in ("PASS", "FAIL"):
        raise HTTPException(status_code=400, detail="Verdict must be PASS or FAIL.")

    trace = db.query(Trace).filter(Trace.id == reviewer_token.trace_id).first()
    trace.human_verdict = verdict
    trace.human_notes   = notes
    trace.eval_status   = EvalStatus.PASS if verdict == "PASS" else EvalStatus.FAIL

    reviewer_token.used = True
    db.commit()

    job = db.query(Job).filter(Job.id == trace.job_id).first()
    pending = db.query(Trace).filter(
        Trace.job_id == trace.job_id,
        Trace.eval_status == EvalStatus.NEEDS_REVIEW
    ).count()

    if pending == 0:
        job.status = JobStatus.COMPLETE
        db.commit()
        send_email(
            to=settings.OPERATOR_EMAIL,
            subject=f"All traces reviewed for {job.company_name}",
            html=(
                f"<p>All traces for <strong>{job.company_name}</strong> have been reviewed. "
                f"Job is now COMPLETE.</p>"
                f"<p><a href='{settings.BASE_URL}/admin/job/{job.id}'>View in admin</a></p>"
            ),
        )

    return HTMLResponse("""
    <html>
    <head>
      <meta charset="UTF-8">
      <link rel="stylesheet" href="/static/style.css">
      <title>Verdict Submitted</title>
    </head>
    <body style="background:var(--color-surface-2);min-height:100vh;display:flex;align-items:center;justify-content:center;">
      <div style="text-align:center;max-width:400px;padding:48px 24px;">
        <div style="font-size:48px;margin-bottom:16px;">✓</div>
        <h2 style="font-size:24px;font-weight:700;margin-bottom:12px;">Verdict submitted.</h2>
        <p style="font-size:17px;color:var(--color-mid);">Thank you. Your assessment has been recorded.</p>
      </div>
    </body>
    </html>
    """)
