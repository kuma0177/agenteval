import os
import re
from collections import defaultdict
from datetime import date

import anthropic

from config import settings
from models import EvalStatus, Job, Trace


def _pass_rate_color(rate: float) -> str:
    if rate >= 70:
        return "#1d8348"
    if rate >= 40:
        return "#e67e22"
    return "#b03a2e"


def _row_bg(verdict: str) -> str:
    if verdict == "PASS":
        return "#eafaf1"
    if verdict == "FAIL":
        return "#fdf2f0"
    return "#f9f9f9"


def _parse_recommendations(text: str) -> list:
    """Split numbered-list text into up to 3 recommendation strings."""
    parts = re.split(r"\n?\s*[1-3]\.\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    return parts[:3]


def _get_recommendations(pass_rate: float, total: int, fail_traces, category_counts: dict) -> str:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    breakdown_lines = []
    for cat, count in category_counts.items():
        example = next(
            (t.llm_reasoning or "" for t in fail_traces if t.failure_category == cat), ""
        )
        example_snippet = (example[:120] + "...") if len(example) > 120 else example
        breakdown_lines.append(f"  {cat}: {count} failure(s). Example: {example_snippet}")
    breakdown = "\n".join(breakdown_lines) if breakdown_lines else "  No categorized failures."

    prompt = (
        f"Based on these agent evaluation findings:\n"
        f"Pass rate: {pass_rate:.1f}%, Total traces: {total}\n"
        f"Failure breakdown:\n{breakdown}\n\n"
        "Write exactly 3 specific, actionable recommendations to improve this agent. "
        "Each must reference a specific failure pattern from the data and give a concrete "
        "technical fix an engineer can implement in 1-2 days. Numbered list."
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return (
            "1. Review and fix the most common failure pattern identified above.\n"
            "2. Add input validation to prevent policy violations.\n"
            "3. Implement loop detection to prevent infinite agent loops."
        )


def generate_report(job_id: str, db_session) -> str:
    job = db_session.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")

    traces = db_session.query(Trace).filter(Trace.job_id == job_id).all()
    total = len(traces)

    pass_traces = [t for t in traces if t.eval_status == EvalStatus.PASS]
    fail_traces = [t for t in traces if t.eval_status == EvalStatus.FAIL]
    review_traces = [t for t in traces if t.eval_status == EvalStatus.NEEDS_REVIEW]

    pass_count = len(pass_traces)
    pass_rate = (pass_count / total * 100) if total else 0.0
    pr_color = _pass_rate_color(pass_rate)
    report_date = date.today().strftime("%B %d, %Y")

    # Category counts (only from FAIL traces)
    category_counts: dict = defaultdict(int)
    for t in fail_traces:
        cat = t.failure_category or "OTHER"
        category_counts[cat] += 1

    # LLM recommendations
    rec_text = _get_recommendations(pass_rate, total, fail_traces, dict(category_counts))
    recommendations = _parse_recommendations(rec_text)
    while len(recommendations) < 3:
        recommendations.append("No additional recommendation available.")

    # ── Summary paragraph ──────────────────────────────────────────────────
    if total == 0:
        summary_para = "No traces were submitted for evaluation."
    else:
        adj = "strong" if pass_rate >= 70 else ("moderate" if pass_rate >= 40 else "poor")
        summary_para = (
            f"The agent demonstrated {adj} reliability across {total} evaluated traces, "
            f"achieving a pass rate of {pass_rate:.1f}%. "
            f"{pass_count} trace(s) passed automated evaluation outright, "
            f"{len(fail_traces)} trace(s) were marked as failures, and "
            f"{len(review_traces)} trace(s) required human review. "
            "See the sections below for a detailed breakdown of failure patterns and recommendations."
        )

    # ── Build trace rows ───────────────────────────────────────────────────
    trace_rows_html = ""
    for i, t in enumerate(traces, 1):
        bg = _row_bg(t.eval_status.value if t.eval_status else "")
        score_str = f"{t.llm_score:.2f}" if t.llm_score is not None else "—"
        cat_str = t.failure_category or "—"
        outcome_escaped = (t.outcome or "")[:80].replace("<", "&lt;").replace(">", "&gt;")
        trace_rows_html += (
            f'<tr style="background:{bg};">'
            f"<td>{i}</td>"
            f"<td>{outcome_escaped}</td>"
            f'<td><strong>{t.eval_status.value if t.eval_status else "—"}</strong></td>'
            f"<td>{score_str}</td>"
            f"<td>{cat_str}</td>"
            "</tr>"
        )

    # ── Heatmap bars ───────────────────────────────────────────────────────
    heatmap_html = ""
    if category_counts:
        max_count = max(category_counts.values())
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            pct = (count / len(fail_traces) * 100) if fail_traces else 0
            bar_width = int((count / max_count) * 100)
            heatmap_html += f"""
            <tr>
              <td style="padding:8px 12px;font-weight:600;width:200px;">{cat}</td>
              <td style="padding:8px 12px;width:60px;text-align:right;">{count}</td>
              <td style="padding:8px 12px;width:70px;text-align:right;">{pct:.0f}%</td>
              <td style="padding:8px 12px;">
                <div style="background:#2e86de;height:18px;width:{bar_width}%;border-radius:3px;"></div>
              </td>
            </tr>"""
    else:
        heatmap_html = '<tr><td colspan="4" style="padding:12px;color:#888;">No failures to display.</td></tr>'

    # ── Root cause groups ──────────────────────────────────────────────────
    fail_groups: dict = defaultdict(list)
    for t in fail_traces:
        fail_groups[t.failure_category or "OTHER"].append(t)

    rca_html = ""
    for cat, group in fail_groups.items():
        rca_html += f'<h3 style="color:#2e86de;margin:24px 0 8px;">{cat}</h3>'
        for t in group:
            notes_section = ""
            if t.human_notes:
                notes_section = f'<p><strong>Human notes:</strong> {t.human_notes}</p>'
            reasoning = (t.llm_reasoning or "No reasoning provided.").replace("<", "&lt;").replace(">", "&gt;")
            detail = (t.failure_detail or "").replace("<", "&lt;").replace(">", "&gt;")
            score_str = f"{t.llm_score:.2f}" if t.llm_score is not None else "—"
            outcome_escaped = (t.outcome or "").replace("<", "&lt;").replace(">", "&gt;")
            rca_html += f"""
            <div style="border:1px solid #e0e0e0;border-radius:6px;padding:16px;margin-bottom:16px;">
              <p><strong>Task:</strong> {outcome_escaped}</p>
              <p><strong>Verdict:</strong> {t.llm_verdict or "—"} &nbsp;|&nbsp; <strong>Score:</strong> {score_str}</p>
              <p><strong>Reasoning:</strong> {reasoning}</p>
              {"<p><strong>Detail:</strong> " + detail + "</p>" if detail else ""}
              {notes_section}
            </div>"""

    if not rca_html:
        rca_html = '<p style="color:#888;">No failures recorded.</p>'

    # ── Recommendation cards ───────────────────────────────────────────────
    rec_cards_html = ""
    for i, rec in enumerate(recommendations, 1):
        rec_escaped = rec.replace("<", "&lt;").replace(">", "&gt;")
        rec_cards_html += f"""
        <div style="display:flex;align-items:flex-start;gap:16px;
                    border:1px solid #d6eaf8;border-radius:8px;padding:20px;
                    margin-bottom:16px;background:#f0f8ff;">
          <div style="min-width:36px;height:36px;border-radius:50%;background:#2e86de;
                      color:#fff;font-size:18px;font-weight:700;display:flex;
                      align-items:center;justify-content:center;">{i}</div>
          <p style="margin:0;line-height:1.6;">{rec_escaped}</p>
        </div>"""

    # ── HTML assembly ──────────────────────────────────────────────────────
    company_escaped = job.company_name.replace("<", "&lt;").replace(">", "&gt;")
    calendly = settings.CALENDLY_URL or "#"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    margin: 2cm 2cm 2.5cm 2cm;
    @bottom-center {{
      content: "AgentEval Agent Reliability Audit \00b7 {company_escaped} \00b7 Confidential";
      font-size: 9pt;
      color: #888;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    color: #111;
    background: #fff;
    margin: 0;
    font-size: 11pt;
    line-height: 1.5;
  }}
  h1 {{ font-size: 28pt; font-weight: 700; margin: 0 0 12px; }}
  h2 {{ font-size: 16pt; font-weight: 700; color: #2e86de; margin: 0 0 16px; border-bottom: 2px solid #2e86de; padding-bottom: 6px; }}
  h3 {{ font-size: 13pt; font-weight: 700; margin: 0 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
  th {{ background: #2e86de; color: #fff; padding: 10px 12px; text-align: left; font-size: 10pt; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #e8e8e8; font-size: 10pt; vertical-align: top; }}
  .section {{ margin-bottom: 40px; }}
  .cover {{ text-align: center; padding: 120px 40px; page-break-after: always; }}
  .page-break {{ page-break-before: always; }}
  .metric-box {{ display: inline-block; text-align: center; padding: 20px 32px;
                 border: 2px solid #e0e0e0; border-radius: 8px; margin: 8px; }}
</style>
</head>
<body>

<!-- SECTION 1: COVER PAGE -->
<div class="cover">
  <h1>Agent Reliability Audit</h1>
  <p style="font-size:22pt;font-weight:700;color:#2e86de;margin:8px 0 32px;">{company_escaped}</p>
  <p style="font-size:12pt;color:#555;margin:0;">Prepared by AgentEval &nbsp;&middot;&nbsp; {report_date} &nbsp;&middot;&nbsp; Confidential</p>
</div>

<!-- SECTION 2: EXECUTIVE SUMMARY -->
<div class="section page-break">
  <h2>Executive Summary</h2>
  <div style="text-align:center;margin-bottom:28px;">
    <span style="font-size:60pt;font-weight:700;color:{pr_color};">{pass_rate:.0f}%</span>
    <p style="font-size:13pt;color:#555;margin:4px 0 0;">Pass Rate</p>
  </div>
  <p>{summary_para}</p>
  <table style="margin-top:24px;">
    <thead><tr>
      <th>Total Traces</th><th>Pass Rate</th><th>Human-Reviewed</th><th>Report Date</th>
    </tr></thead>
    <tbody><tr>
      <td style="background:#fff;">{total}</td>
      <td style="background:#fff;">{pass_rate:.1f}%</td>
      <td style="background:#fff;">{len(review_traces)}</td>
      <td style="background:#fff;">{report_date}</td>
    </tr></tbody>
  </table>
</div>

<!-- SECTION 3: PASS/FAIL TABLE -->
<div class="section page-break">
  <h2>Pass / Fail Results</h2>
  <table>
    <thead><tr>
      <th>#</th><th>Task</th><th>Verdict</th><th>Score</th><th>Category</th>
    </tr></thead>
    <tbody>{trace_rows_html}</tbody>
  </table>
</div>

<!-- SECTION 4: FAILURE HEATMAP -->
<div class="section page-break">
  <h2>Failure Heatmap</h2>
  <table>
    <thead><tr>
      <th>Category</th><th>Count</th><th>Percentage</th><th>Volume</th>
    </tr></thead>
    <tbody>{heatmap_html}</tbody>
  </table>
</div>

<!-- SECTION 5: ROOT CAUSE ANALYSIS -->
<div class="section page-break">
  <h2>Root Cause Analysis</h2>
  {rca_html}
</div>

<!-- SECTION 6: TOP 3 RECOMMENDATIONS -->
<div class="section page-break">
  <h2>Top 3 Recommendations</h2>
  {rec_cards_html}
</div>

<!-- SECTION 7: NEXT STEPS -->
<div class="section page-break">
  <h2>Next Steps</h2>
  <p style="font-size:13pt;margin-bottom:12px;">
    <strong>Schedule your debrief:</strong>
    <a href="{calendly}" style="color:#2e86de;">{calendly}</a>
  </p>
  <p style="font-size:13pt;">
    <strong>Questions?</strong> Email
    <a href="mailto:hello@agenteval.com" style="color:#2e86de;">hello@agenteval.com</a>
  </p>
</div>

</body>
</html>"""

    os.makedirs(settings.REPORT_DIR, exist_ok=True)
    output_path = os.path.join(settings.REPORT_DIR, f"{job_id}.pdf")

    from weasyprint import HTML
    HTML(string=html_content).write_pdf(output_path)

    job.report_path = output_path
    db_session.commit()

    return output_path
