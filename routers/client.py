import json

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Job, Trace, JobStatus
from config import settings
from services.stripe_service import create_checkout_session

router = APIRouter(tags=["client"])
templates = Jinja2Templates(directory="templates")


def _get_job_or_404(token: str, db: Session) -> Job:
    job = db.query(Job).filter(Job.access_token == token).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. Contact hello@agenteval.com")
    return job


# ── Intake ──────────────────────────────────────────────────────────────────

@router.get("/intake/{access_token}", response_class=HTMLResponse)
def intake_page(access_token: str, request: Request, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)
    if job.status not in (JobStatus.INTAKE,):
        return RedirectResponse(url=f"/submit/{access_token}", status_code=302)
    return templates.TemplateResponse("intake.html", {"request": request, "job": job, "config": settings})


@router.post("/intake/{access_token}/checkout")
def intake_checkout(access_token: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)
    success_url = f"{settings.BASE_URL}/submit/{access_token}?payment=success"
    cancel_url  = f"{settings.BASE_URL}/intake/{access_token}?cancelled=true"
    checkout_url = create_checkout_session(
        job_id=job.id,
        price_id=settings.STRIPE_PRICE_ID_STARTER,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    job.stripe_session = checkout_url  # will be overwritten by webhook with real session ID
    db.commit()
    return RedirectResponse(url=checkout_url, status_code=303)


# ── Submission ───────────────────────────────────────────────────────────────

@router.get("/submit/{access_token}", response_class=HTMLResponse)
def submit_page(
    access_token: str,
    request: Request,
    submitted: str = None,
    payment: str = None,
    db: Session = Depends(get_db),
):
    job = _get_job_or_404(access_token, db)

    if job.status == JobStatus.INTAKE:
        return RedirectResponse(url=f"/intake/{access_token}", status_code=302)

    if submitted == "true" or job.status in (JobStatus.SUBMITTED, JobStatus.EVALUATING, JobStatus.REVIEW, JobStatus.COMPLETE):
        trace_count = db.query(Trace).filter(Trace.job_id == job.id).count()
        return templates.TemplateResponse("status.html", {
            "request": request,
            "job": job,
            "trace_count": trace_count,
            "config": settings,
        })

    return templates.TemplateResponse("submit.html", {
        "request": request,
        "job": job,
        "access_token": access_token,
        "config": settings,
    })


@router.post("/submit/{access_token}")
async def submit_traces(
    access_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    from services.email_service import send_email

    job = _get_job_or_404(access_token, db)

    form = await request.form()
    raw_traces = form.getlist("traces[]")
    outcomes   = form.getlist("outcomes[]")

    trace_file = form.get("trace_file")
    if trace_file and hasattr(trace_file, "read"):
        content = await trace_file.read()
        if content:
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    for item in data:
                        raw_traces.append(json.dumps(item))
                        outcomes.append(item.get("outcome", "Unknown"))
                else:
                    raw_traces.append(content.decode())
                    outcomes.append("Uploaded trace")
            except Exception:
                pass

    saved = 0
    for i, raw in enumerate(raw_traces):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {}
        messages = parsed.get("messages", [])
        turn_count = len([m for m in messages if m.get("role") == "assistant"])
        outcome = outcomes[i] if i < len(outcomes) else "Unknown"
        trace = Trace(
            job_id=job.id,
            raw_json=raw,
            turn_count=turn_count,
            outcome=outcome,
        )
        db.add(trace)
        saved += 1

    if saved:
        job.status = JobStatus.SUBMITTED
        db.commit()

        send_email(
            to=settings.OPERATOR_EMAIL,
            subject=f"{job.company_name} submitted {saved} traces — ready for evaluation",
            html=f"<p>{job.company_name} submitted {saved} traces.</p>"
                 f"<p><a href='{settings.BASE_URL}/admin/job/{job.id}'>View in admin</a></p>",
        )

    return RedirectResponse(url=f"/submit/{access_token}?submitted=true", status_code=303)
