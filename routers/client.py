import json
import os

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import auth as auth_module
from config import settings
from database import get_db
from models import Job, JobStatus, Trace
from services.stripe_service import create_checkout_session

router = APIRouter(tags=["client"])
templates = Jinja2Templates(directory="templates")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_job_or_404(token: str, db: Session) -> Job:
    job = db.query(Job).filter(Job.access_token == token).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. Contact hello@agenteval.com")
    return job


def _require_client_auth(request: Request, access_token: str, db: Session):
    """Returns Job if authenticated, or RedirectResponse if not."""
    cookie = request.cookies.get("client_session")
    login_url = f"/client/{access_token}/login"
    if not cookie:
        return RedirectResponse(url=login_url, status_code=302)
    job_id = auth_module.verify_client_session(cookie)
    if not job_id:
        return RedirectResponse(url=login_url, status_code=302)
    job = db.query(Job).filter(Job.access_token == access_token).first()
    if not job or job.id != job_id:
        return RedirectResponse(url=login_url, status_code=302)
    return job


def _has_valid_session(request: Request, access_token: str, db: Session) -> bool:
    cookie = request.cookies.get("client_session")
    if not cookie:
        return False
    job_id = auth_module.verify_client_session(cookie)
    if not job_id:
        return False
    job = db.query(Job).filter(Job.access_token == access_token).first()
    return bool(job and job.id == job_id)


# ── Intake ────────────────────────────────────────────────────────────────────

@router.get("/intake/{access_token}", response_class=HTMLResponse)
def intake_page(access_token: str, request: Request, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)
    beyond_intake = job.status not in (JobStatus.INTAKE,)
    if beyond_intake:
        return RedirectResponse(url=f"/client/{access_token}/login", status_code=302)
    return templates.TemplateResponse("intake.html", {"request": request, "job": job, "config": settings})


@router.post("/intake/{access_token}/checkout")
def intake_checkout(access_token: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)
    success_url = f"{settings.BASE_URL}/client/{access_token}/setup-password"
    cancel_url  = f"{settings.BASE_URL}/intake/{access_token}"
    session_id, session_url = create_checkout_session(
        job_id=job.id,
        price_id=settings.STRIPE_PRICE_ID_STARTER,
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=job.contact_email,
    )
    job.stripe_session = session_id
    db.commit()
    return RedirectResponse(url=session_url, status_code=303)


# ── Portal Auth ───────────────────────────────────────────────────────────────

@router.get("/client/{access_token}/setup-password", response_class=HTMLResponse)
def setup_password_page(access_token: str, request: Request, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)
    if job.status != JobStatus.PAID:
        return RedirectResponse(url=f"/intake/{access_token}", status_code=302)
    if job.client_password_hash:
        return RedirectResponse(url=f"/client/{access_token}/login", status_code=302)
    return templates.TemplateResponse("portal_setup.html", {"request": request, "job": job})


@router.post("/client/{access_token}/setup-password")
async def setup_password_post(access_token: str, request: Request, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)
    if job.status != JobStatus.PAID:
        return RedirectResponse(url=f"/intake/{access_token}", status_code=302)

    form = await request.form()
    password = form.get("password", "")
    confirm  = form.get("confirm_password", "")

    error = None
    if len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm:
        error = "Passwords do not match."

    if error:
        return templates.TemplateResponse(
            "portal_setup.html",
            {"request": request, "job": job, "error": error},
            status_code=400,
        )

    job.client_password_hash = _pwd_context.hash(password)
    db.commit()

    token = auth_module.create_client_session(job.id)
    response = RedirectResponse(url=f"/client/{access_token}/dashboard", status_code=303)
    response.set_cookie(
        "client_session", token,
        httponly=True, samesite="lax", max_age=2592000,
    )
    return response


@router.get("/client/{access_token}/login", response_class=HTMLResponse)
def login_page(
    access_token: str,
    request: Request,
    msg: str = None,
    db: Session = Depends(get_db),
):
    job = _get_job_or_404(access_token, db)
    if _has_valid_session(request, access_token, db):
        return RedirectResponse(url=f"/client/{access_token}/dashboard", status_code=302)
    return templates.TemplateResponse(
        "portal_login.html",
        {"request": request, "job": job, "msg": msg},
    )


@router.post("/client/{access_token}/login")
async def login_post(access_token: str, request: Request, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)

    form = await request.form()
    password = form.get("password", "")

    if not job.client_password_hash or not _pwd_context.verify(password, job.client_password_hash):
        return templates.TemplateResponse(
            "portal_login.html",
            {"request": request, "job": job, "error": "Incorrect password."},
            status_code=400,
        )

    token = auth_module.create_client_session(job.id)
    response = RedirectResponse(url=f"/client/{access_token}/dashboard", status_code=303)
    response.set_cookie(
        "client_session", token,
        httponly=True, samesite="lax", max_age=2592000,
    )
    return response


@router.get("/client/{access_token}/logout")
def logout(access_token: str):
    response = RedirectResponse(
        url=f"/client/{access_token}/login?msg=Signed+out+successfully",
        status_code=302,
    )
    response.delete_cookie("client_session")
    return response


# ── Trace Submission (portal) ─────────────────────────────────────────────────

@router.get("/client/{access_token}/submit", response_class=HTMLResponse)
def portal_submit_page(access_token: str, request: Request, db: Session = Depends(get_db)):
    auth_result = _require_client_auth(request, access_token, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    job = auth_result

    if job.status != JobStatus.PAID:
        if job.status in (JobStatus.SUBMITTED, JobStatus.EVALUATING, JobStatus.REVIEW, JobStatus.COMPLETE):
            return RedirectResponse(url=f"/client/{access_token}/dashboard", status_code=302)
        return templates.TemplateResponse(
            "portal_error.html",
            {"request": request, "job": job, "message": "Payment not confirmed."},
            status_code=402,
        )

    return templates.TemplateResponse(
        "submit.html",
        {"request": request, "job": job, "access_token": access_token, "config": settings},
    )


@router.post("/client/{access_token}/submit")
async def portal_submit_post(access_token: str, request: Request, db: Session = Depends(get_db)):
    auth_result = _require_client_auth(request, access_token, db)
    if isinstance(auth_result, RedirectResponse):
        return auth_result
    job = auth_result

    from services.email_service import send_evaluation_started, send_traces_submitted_alert

    form = await request.form()
    raw_traces = list(form.getlist("traces[]"))
    outcomes   = list(form.getlist("outcomes[]"))

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
        messages  = parsed.get("messages", [])
        turn_count = len([m for m in messages if m.get("role") == "assistant"])
        outcome   = outcomes[i] if i < len(outcomes) else parsed.get("outcome", "Unknown")
        metadata  = parsed.get("metadata", {})
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

        send_evaluation_started(job, saved, db)
        send_traces_submitted_alert(job, saved, db)

    return RedirectResponse(url=f"/client/{access_token}/dashboard", status_code=303)


# ── Legacy submit routes (kept for backward compat) ───────────────────────────

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


# ── Report ─────────────────────────────────────────────────────────────────────

_STATUS_LABELS = {
    JobStatus.INTAKE: ("Intake form", 1),
    JobStatus.PAID: ("Payment received", 2),
    JobStatus.SUBMITTED: ("Traces submitted", 3),
    JobStatus.EVALUATING: ("LLM evaluation in progress", 4),
    JobStatus.REVIEW: ("Human review in progress", 5),
    JobStatus.COMPLETE: ("Report ready", 6),
}


def _timeline_html(current_status: JobStatus) -> str:
    steps = [
        (JobStatus.INTAKE, "Intake"),
        (JobStatus.PAID, "Payment"),
        (JobStatus.SUBMITTED, "Traces submitted"),
        (JobStatus.EVALUATING, "Evaluation"),
        (JobStatus.REVIEW, "Human review"),
        (JobStatus.COMPLETE, "Report ready"),
    ]
    current_idx = next((i for i, (s, _) in enumerate(steps) if s == current_status), 0)
    items = ""
    for i, (_, label) in enumerate(steps):
        if i < current_idx:
            color, icon = "#1d8348", "&#10003;"
        elif i == current_idx:
            color, icon = "#2e86de", "&#9679;"
        else:
            color, icon = "#ccc", "&#9675;"
        items += (
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
            f'<span style="font-size:20px;color:{color};">{icon}</span>'
            f'<span style="color:{color};font-weight:{"700" if i == current_idx else "400"};">{label}</span>'
            f"</div>"
        )
    return items


@router.get("/report/{access_token}", response_class=HTMLResponse)
def report_page(access_token: str, request: Request, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)

    report_ready = job.status == JobStatus.COMPLETE and job.report_path and os.path.exists(job.report_path)

    if not report_ready:
        label, _ = _STATUS_LABELS.get(job.status, ("In progress", 0))
        timeline = _timeline_html(job.status)
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Report Status — AgentEval</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body style="background:var(--color-surface-2,#f5f6fa);min-height:100vh;display:flex;align-items:center;justify-content:center;">
  <div style="max-width:480px;width:100%;background:#fff;border-radius:12px;padding:40px;box-shadow:0 2px 16px rgba(0,0,0,.08);">
    <h1 style="font-size:22px;font-weight:700;margin-bottom:8px;">Report not ready yet</h1>
    <p style="color:#555;margin-bottom:28px;">Current status: <strong>{label}</strong></p>
    <div>{timeline}</div>
    <p style="color:#888;font-size:14px;margin-top:24px;">
      This page does not auto-refresh. Check back soon or email
      <a href="mailto:hello@agenteval.com">hello@agenteval.com</a> with questions.
    </p>
  </div>
</body>
</html>"""
        return HTMLResponse(html)

    download_url = f"/report/{access_token}/download"
    calendly = settings.CALENDLY_URL or "#"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Your Report is Ready — AgentEval</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body style="background:var(--color-surface-2,#f5f6fa);min-height:100vh;display:flex;align-items:center;justify-content:center;">
  <div style="max-width:480px;width:100%;background:#fff;border-radius:12px;padding:40px;box-shadow:0 2px 16px rgba(0,0,0,.08);text-align:center;">
    <div style="font-size:48px;margin-bottom:16px;">&#10003;</div>
    <h1 style="font-size:24px;font-weight:700;margin-bottom:8px;">Your report is ready</h1>
    <p style="color:#555;margin-bottom:28px;">
      Your Agent Reliability Audit for <strong>{job.company_name}</strong> is complete.
    </p>
    <a href="{download_url}"
       style="display:inline-block;background:#2e86de;color:#fff;padding:14px 32px;
              border-radius:8px;text-decoration:none;font-weight:700;font-size:16px;
              margin-bottom:20px;">
      &#8595; Download PDF Report
    </a>
    <p style="color:#555;margin-top:20px;">
      Want to walk through the findings with us?<br>
      <a href="{calendly}" style="color:#2e86de;font-weight:600;">Book your debrief call &rarr;</a>
    </p>
    <p style="color:#aaa;font-size:13px;margin-top:24px;">
      Questions? <a href="mailto:hello@agenteval.com" style="color:#888;">hello@agenteval.com</a>
    </p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/report/{access_token}/download")
def report_download(access_token: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(access_token, db)

    if job.status != JobStatus.COMPLETE or not job.report_path:
        raise HTTPException(status_code=404, detail="Report not available yet.")
    if not os.path.exists(job.report_path):
        raise HTTPException(status_code=404, detail="Report file not found. Contact hello@agenteval.com")

    filename = f"AgentEval-Report-{job.company_name.replace(' ', '-')}.pdf"
    return FileResponse(
        path=job.report_path,
        media_type="application/pdf",
        filename=filename,
    )
