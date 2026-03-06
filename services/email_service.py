import requests

from config import settings


def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via the Resend API. Returns True on success."""
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        },
    )
    return response.status_code == 200


def send_intake_confirmation(contact_email: str, contact_name: str, access_token: str) -> bool:
    subject = "AgentEval — We received your submission"
    html = f"""
    <p>Hi {contact_name},</p>
    <p>Thank you for submitting your agent for evaluation. We've received your intake form.</p>
    <p>You can track your evaluation status using your client portal link:</p>
    <p><a href="{settings.BASE_URL}/client/{access_token}">{settings.BASE_URL}/client/{access_token}</a></p>
    <p>We'll be in touch with next steps shortly.</p>
    <p>— The AgentEval Team</p>
    """
    return send_email(contact_email, subject, html)


def send_report_ready(contact_email: str, contact_name: str, access_token: str) -> bool:
    subject = "AgentEval — Your evaluation report is ready"
    html = f"""
    <p>Hi {contact_name},</p>
    <p>Your agent evaluation is complete. You can download your report from your client portal:</p>
    <p><a href="{settings.BASE_URL}/client/{access_token}">{settings.BASE_URL}/client/{access_token}</a></p>
    <p>Thank you for using AgentEval.</p>
    <p>— The AgentEval Team</p>
    """
    return send_email(contact_email, subject, html)
