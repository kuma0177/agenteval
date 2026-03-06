from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Job, JobStatus
from config import settings
from services.email_service import send_email

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    import stripe

    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        job_id  = session.get("metadata", {}).get("job_id")

        if job_id:
            db: Session = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = JobStatus.PAID
                    job.stripe_session = session.get("id")
                    db.commit()

                    # Email client
                    send_email(
                        to=job.contact_email,
                        subject="Payment confirmed — submit your traces",
                        html=f"""
                        <p>Hi {job.contact_name},</p>
                        <p>Payment confirmed! You can now submit your agent traces.</p>
                        <p><a href="{settings.BASE_URL}/submit/{job.access_token}">Submit your traces here</a></p>
                        <h3>Expected JSON format</h3>
                        <pre>{{
  "messages": [
    {{"role": "user", "content": "Your user message"}},
    {{"role": "assistant", "content": "Agent response",
     "tool_calls": [{{"name": "tool_name", "input": {{}}}}]}},
    {{"role": "tool", "content": "Tool result"}},
    {{"role": "assistant", "content": "Final response"}}
  ]
}}</pre>
                        <p>— The AgentEval Team</p>
                        """,
                    )

                    # Email operator
                    send_email(
                        to=settings.OPERATOR_EMAIL,
                        subject=f"{job.company_name} paid — job ready",
                        html=f"""
                        <p><strong>{job.company_name}</strong> has paid.</p>
                        <p>Contact: {job.contact_name} ({job.contact_email})</p>
                        <p><a href="{settings.BASE_URL}/admin/job/{job.id}">View job in admin</a></p>
                        """,
                    )
            finally:
                db.close()

    return {"ok": True}
