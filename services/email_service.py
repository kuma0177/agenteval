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


# ── Client emails ──────────────────────────────────────────────────────────────

def send_intake_email(job) -> bool:
    intake_url = f"{settings.BASE_URL}/intake/{job.access_token}"
    calendly = settings.CALENDLY_URL or "#"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#111;">
      <h2 style="color:#2e86de;">Your AgentEval audit is ready to begin</h2>
      <p>Hi {job.contact_name},</p>
      <p>We're excited to evaluate your AI agent. Here's what happens next:</p>
      <ol>
        <li>Complete your intake form at the link below</li>
        <li>Submit payment to unlock the trace submission portal</li>
        <li>Upload your agent conversation traces (JSON format)</li>
        <li>Our LLM judge evaluates each trace automatically</li>
        <li>You receive a full PDF reliability report with recommendations</li>
      </ol>
      <p style="margin:24px 0;">
        <a href="{intake_url}"
           style="background:#2e86de;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;font-weight:700;">Begin Intake &rarr;</a>
      </p>
      <p>Want to book your debrief call in advance?
         <a href="{calendly}" style="color:#2e86de;">Schedule on Calendly</a></p>
      <p style="color:#888;font-size:13px;">— The AgentEval Team &nbsp;|&nbsp; hello@agenteval.com</p>
    </div>
    """
    return send_email(job.contact_email, "Your AgentEval audit is ready to begin", html)


def send_payment_confirmed_email(job) -> bool:
    submit_url = f"{settings.BASE_URL}/submit/{job.access_token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#111;">
      <h2 style="color:#2e86de;">Payment confirmed — submit your traces</h2>
      <p>Hi {job.contact_name},</p>
      <p>Your payment has been received. You can now submit your agent traces for evaluation.</p>
      <p style="margin:24px 0;">
        <a href="{submit_url}"
           style="background:#2e86de;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;font-weight:700;">Submit Traces &rarr;</a>
      </p>
      <h3>Trace format guide</h3>
      <p>Each trace should be a JSON object with at minimum a <code>messages</code> array
         and an <code>outcome</code> string describing the task goal.</p>
      <p>Example:</p>
      <pre style="background:#f5f5f5;padding:16px;border-radius:6px;font-size:13px;">
{{
  "outcome": "Book a flight from NYC to London for next Tuesday",
  "messages": [
    {{"role": "user", "content": "Book me a flight to London next Tuesday"}},
    {{"role": "assistant", "content": "...", "tool_calls": [
      {{"name": "search_flights", "arguments": {{"origin":"JFK","destination":"LHR"}}}}
    ]}},
    {{"role": "tool", "content": "Found 3 flights..."}},
    {{"role": "assistant", "content": "I found the following options..."}}
  ]
}}</pre>
      <p>Include all tool calls and tool responses in the messages array for the most
         accurate evaluation.</p>
      <p style="color:#888;font-size:13px;">— The AgentEval Team &nbsp;|&nbsp; hello@agenteval.com</p>
    </div>
    """
    return send_email(job.contact_email, "Payment confirmed — submit your traces", html)


def send_report_ready_email(job) -> bool:
    report_url = f"{settings.BASE_URL}/report/{job.access_token}"
    calendly = settings.CALENDLY_URL or "#"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#111;">
      <h2 style="color:#2e86de;">Your AgentEval report is ready</h2>
      <p>Hi {job.contact_name},</p>
      <p>Your Agent Reliability Audit is complete. Your report includes:</p>
      <ul>
        <li>Overall pass rate and executive summary</li>
        <li>Per-trace pass/fail verdicts with scores</li>
        <li>Failure category heatmap</li>
        <li>Root cause analysis for every failure</li>
        <li>3 actionable recommendations for your engineering team</li>
      </ul>
      <p style="margin:24px 0;">
        <a href="{report_url}"
           style="background:#2e86de;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;font-weight:700;">Download Report &rarr;</a>
      </p>
      <p>Ready to discuss the findings?
         <a href="{calendly}" style="color:#2e86de;">Book your debrief call</a></p>
      <p style="color:#888;font-size:13px;">— The AgentEval Team &nbsp;|&nbsp; hello@agenteval.com</p>
    </div>
    """
    return send_email(job.contact_email, "Your AgentEval report is ready", html)


def send_reviewer_email(reviewer_email: str, trace, token_str: str) -> bool:
    review_url = f"{settings.BASE_URL}/review/{token_str}"
    outcome_snippet = (trace.outcome or "")[:200]
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#111;">
      <h2 style="color:#2e86de;">Expert review needed — 5 minutes</h2>
      <p>An AI agent trace has been flagged as UNCERTAIN and needs a human verdict.
         This should take about 5 minutes.</p>
      <h3>Task description</h3>
      <p style="background:#f5f5f5;padding:12px;border-radius:6px;">{outcome_snippet}</p>
      <p style="margin:24px 0;">
        <a href="{review_url}"
           style="background:#2e86de;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;font-weight:700;">Review This Trace &rarr;</a>
      </p>
      <p style="color:#888;font-size:13px;">
        This is a one-time link. Please do not share it.<br>
        — AgentEval &nbsp;|&nbsp; hello@agenteval.com
      </p>
    </div>
    """
    return send_email(reviewer_email, "Expert review needed — 5 minutes — AgentEval", html)


# ── Legacy helpers (still used by existing routers) ────────────────────────────

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
