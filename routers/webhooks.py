from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Job, JobStatus
from config import settings

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

                    from services.email_service import send_payment_confirmed, send_payment_received_alert
                    send_payment_confirmed(job, db)
                    send_payment_received_alert(job, db)
            finally:
                db.close()

    return {"ok": True}
