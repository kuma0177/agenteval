import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import settings


def _send_via_resend(to: str, subject: str, html: str) -> bool:
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"from": settings.RESEND_FROM_EMAIL, "to": [to], "subject": subject, "html": html},
    )
    if response.status_code not in (200, 201):
        print(f"[email] Resend FAILED ({response.status_code}): {response.text[:200]}")
        return False
    print(f"[email] Sent via Resend to {to}")
    return True


def _send_via_smtp(to: str, subject: str, html: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.SMTP_USERNAME
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USERNAME, to, msg.as_string())
        print(f"[email] Sent via SMTP to {to}")
        return True
    except Exception as e:
        print(f"[email] SMTP FAILED: {e}")
        return False


def send_email(to: str, subject: str, html: str) -> bool:
    """Send via Resend if configured, else fall back to Gmail SMTP."""
    if settings.RESEND_API_KEY and settings.RESEND_FROM_EMAIL:
        return _send_via_resend(to, subject, html)
    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        return _send_via_smtp(to, subject, html)
    print(f"[email] SKIPPED — no email provider configured. Would send to: {to}")
    return False


# ── Lead / sample report email ────────────────────────────────────────────────

def send_sample_report_email(email: str, company: str) -> bool:
    calendly = settings.CALENDLY_URL or "#"
    sample_url = f"{settings.BASE_URL}/static/sample-report.pdf"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;color:#111;line-height:1.6;">
      <h2 style="color:#2e86de;margin-bottom:4px;">Here's what an AgentEval report looks like.</h2>
      <p style="color:#555;margin-top:0;">Thanks for your interest{(' — ' + company) if company else ''}. Below is a sample of the report format you'll receive.</p>
      <hr style="border:none;border-top:1px solid #e8e8e8;margin:24px 0;">

      <!-- Cover -->
      <div style="background:#f0f7ff;border-radius:8px;padding:24px;margin-bottom:20px;text-align:center;">
        <p style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#2e86de;text-transform:uppercase;margin:0 0 8px;">Agent Reliability Audit</p>
        <p style="font-size:20px;font-weight:700;margin:0 0 4px;">Acme Health AI — Sample</p>
        <p style="font-size:12px;color:#888;margin:0;">Prepared by AgentEval &nbsp;·&nbsp; Confidential</p>
      </div>

      <!-- Pass rate -->
      <div style="background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:20px;margin-bottom:20px;text-align:center;">
        <p style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#888;text-transform:uppercase;margin:0 0 4px;">Section 1 — Executive Summary</p>
        <p style="font-size:56px;font-weight:800;color:#1d8348;margin:8px 0 0;line-height:1;">72%</p>
        <p style="color:#555;margin:4px 0 16px;">Overall Pass Rate &nbsp;·&nbsp; 25 traces evaluated</p>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr style="background:#f9f9f9;">
            <td style="padding:8px 12px;border:1px solid #e8e8e8;font-weight:700;">Total Traces</td>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;font-weight:700;">Pass Rate</td>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;font-weight:700;">Human-Reviewed</td>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;font-weight:700;">Failures</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;">25</td>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;color:#1d8348;font-weight:700;">72%</td>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;">4</td>
            <td style="padding:8px 12px;border:1px solid #e8e8e8;color:#b03a2e;">7</td>
          </tr>
        </table>
      </div>

      <!-- Dimension scorecard -->
      <div style="background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:20px;margin-bottom:20px;">
        <p style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#888;text-transform:uppercase;margin:0 0 16px;">Section 4 — Dimension Scorecard</p>
        {''.join(
          f'<div style="margin-bottom:12px;">'
          f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">'
          f'<span>{label}</span><strong style="color:{color};">{pct}%</strong></div>'
          f'<div style="background:#e8e8e8;border-radius:3px;height:8px;">'
          f'<div style="background:{color};width:{pct}%;height:8px;border-radius:3px;"></div></div></div>'
          for label, pct, color in [
            ('Task Completion', 78, '#1d8348'),
            ('Tool Selection', 71, '#1d8348'),
            ('Reasoning Coherence', 82, '#1d8348'),
            ('Policy Compliance', 94, '#1d8348'),
            ('Hallucination Risk', 55, '#e67e22'),
          ]
        )}
      </div>

      <!-- Failure heatmap -->
      <div style="background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:20px;margin-bottom:20px;">
        <p style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#888;text-transform:uppercase;margin:0 0 16px;">Section 5 — Failure Heatmap</p>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          {''.join(
            f'<tr><td style="padding:7px 10px;font-weight:600;width:160px;">{cat}</td>'
            f'<td style="padding:7px 10px;width:40px;color:#888;">{cnt}</td>'
            f'<td style="padding:7px 10px;"><div style="background:#2e86de;height:14px;width:{w}%;border-radius:3px;"></div></td></tr>'
            for cat, cnt, w in [
              ('HALLUCINATION', 3, 100), ('INCOMPLETE', 2, 67), ('WRONG_TOOL', 1, 33), ('LOOP', 1, 33)
            ]
          )}
        </table>
      </div>

      <!-- Top recommendation -->
      <div style="background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:20px;margin-bottom:24px;">
        <p style="font-size:11px;font-weight:700;letter-spacing:.08em;color:#888;text-transform:uppercase;margin:0 0 16px;">Section 7 — Top 3 Recommendations (excerpt)</p>
        <div style="display:flex;gap:14px;align-items:flex-start;padding:14px;background:#f0f7ff;border-radius:6px;">
          <div style="min-width:30px;height:30px;border-radius:50%;background:#2e86de;color:#fff;font-weight:700;font-size:15px;display:flex;align-items:center;justify-content:center;">1</div>
          <p style="margin:0;font-size:13px;line-height:1.6;"><strong>Add citation grounding to reduce hallucination risk.</strong> 3 of 7 failures were traced to the agent generating plausible-sounding but unverified clinical facts. Implement retrieval-augmented generation (RAG) with source citations on all patient-facing responses within the next sprint.</p>
        </div>
      </div>

      <!-- CTA -->
      <div style="text-align:center;padding:24px 0;">
        <p style="font-size:16px;font-weight:600;margin-bottom:16px;">Download the full sample report</p>
        <a href="{sample_url}" style="background:#2e86de;color:#fff;padding:13px 28px;border-radius:7px;text-decoration:none;font-weight:700;font-size:15px;">↓ Download Sample PDF</a>
        <p style="color:#555;font-size:14px;margin-top:24px;margin-bottom:16px;">Ready to audit your own agent?</p>
        <a href="{calendly}" style="background:#111;color:#fff;padding:12px 24px;border-radius:7px;text-decoration:none;font-weight:700;font-size:14px;">Book a Free Discovery Call</a>
        <p style="color:#888;font-size:13px;margin-top:20px;">Questions? Reply to this email or write to <a href="mailto:hello@agenteval.com" style="color:#2e86de;">hello@agenteval.com</a></p>
      </div>

      <hr style="border:none;border-top:1px solid #e8e8e8;margin:24px 0;">
      <p style="color:#aaa;font-size:11px;text-align:center;">AgentEval &nbsp;·&nbsp; hello@agenteval.com &nbsp;·&nbsp; This email was sent because you requested a sample report.</p>
    </div>
    """
    return send_email(email, "Your AgentEval sample report", html)


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


# ── Operator alert: new lead ───────────────────────────────────────────────────

def send_new_lead_alert(lead) -> bool:
    if not settings.OPERATOR_EMAIL:
        return False
    html = (
        f"<p>New lead from <strong>{lead.email}</strong></p>"
        f"<p>Company: {lead.company or '(none)'}</p>"
        f"<p>Description: {lead.agent_description or '(none)'}</p>"
        f"<p><a href='{settings.BASE_URL}/admin'>View in admin</a></p>"
    )
    return send_email(
        to=settings.OPERATOR_EMAIL,
        subject=f"New lead: {lead.email}",
        html=html,
    )


# ── Operator alert: new reviewer application ──────────────────────────────────

def send_new_application_alert(profile) -> bool:
    if not settings.OPERATOR_EMAIL:
        return False
    html = (
        f"<p><strong>{profile.name}</strong> ({profile.email}) applied as a reviewer.</p>"
        f"<p>Domain: {profile.domain_expertise}</p>"
        f"<p>Years experience: {profile.years_experience or '?'}</p>"
        f"<p>Rate: ${profile.hourly_rate_usd or '?'}/review &nbsp;·&nbsp; Availability: {profile.availability or '?'}</p>"
        f"<p>Bio: {profile.bio or '(none)'}</p>"
        f"<p><a href='{settings.BASE_URL}/admin/reviewers'>Review in admin</a></p>"
    )
    return send_email(
        to=settings.OPERATOR_EMAIL,
        subject=f"New reviewer application: {profile.name} ({profile.domain_expertise})",
        html=html,
    )
