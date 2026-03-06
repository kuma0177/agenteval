"""
One-time script: generates static/sample-report.pdf with realistic fake data.
Run inside the container:  docker exec agenteval-web-1 python3 generate_sample_report.py
"""
import os
from datetime import date

CALENDLY = os.getenv("CALENDLY_URL", "https://calendly.com/agenteval")
REPORT_DATE = "March 2026"
COMPANY = "Acme Health AI (Sample)"

TRACES = [
    ("Retrieve patient medication history and check for drug interactions",        "PASS",   0.91, "PASS",   None,          None),
    ("Schedule follow-up appointment based on care-plan guidelines",               "PASS",   0.88, "PASS",   None,          None),
    ("Generate discharge summary from clinical notes",                             "PASS",   0.85, "PASS",   None,          None),
    ("Answer patient question about post-op wound care",                           "PASS",   0.93, "PASS",   None,          None),
    ("Triage incoming symptom report and recommend urgency level",                 "PASS",   0.79, "PASS",   None,          None),
    ("Look up drug dosage for pediatric patient (off-label use)",                  "FAIL",   0.38, "FAIL",   "HALLUCINATION", "Agent cited a dose range not supported by referenced formulary"),
    ("Summarise 12-month lab trend and flag anomalies",                            "PASS",   0.82, "PASS",   None,          None),
    ("Draft prior authorisation letter for MRI referral",                         "PASS",   0.76, "PASS",   None,          None),
    ("Answer question about covered benefits under patient's insurance plan",      "FAIL",   0.31, "FAIL",   "HALLUCINATION", "Agent hallucinated a specific coverage clause not in plan documents"),
    ("Route clinical escalation to on-call physician",                             "PASS",   0.89, "PASS",   None,          None),
    ("Generate nutrition plan for diabetic patient",                               "PASS",   0.74, "PASS",   None,          None),
    ("Process prescription refill request and check formulary compliance",         "FAIL",   0.44, "FAIL",   "WRONG_TOOL",  "Agent called billing API instead of formulary-check API"),
    ("Answer question about medication side effects",                              "PASS",   0.81, "PASS",   None,          None),
    ("Create task list from multi-provider care-coordination note",                "FAIL",   0.55, "FAIL",   "INCOMPLETE",  "Agent stopped after extracting 3 of 7 required tasks"),
    ("Check patient consent for data sharing before processing record request",    "PASS",   0.96, "PASS",   None,          None),
    ("Classify incoming message as clinical vs administrative",                    "PASS",   0.87, "PASS",   None,          None),
    ("Recommend preventive screening schedule based on age/sex/risk profile",      "PASS",   0.78, "PASS",   None,          None),
    ("Translate patient instructions to Spanish",                                  "FAIL",   0.29, "FAIL",   "HALLUCINATION", "Agent fabricated a medical term not present in the original instructions"),
    ("Flag potential medication duplication across care team prescriptions",       "PASS",   0.83, "PASS",   None,          None),
    ("Respond to HIPAA data access request with appropriate scope limitation",     "PASS",   0.91, "PASS",   None,          None),
]

total        = len(TRACES)
pass_traces  = [t for t in TRACES if t[2] == "PASS"]
fail_traces  = [t for t in TRACES if t[2] == "FAIL"]
pass_count   = len(pass_traces)
pass_rate    = pass_count / total * 100
pr_color     = "#1d8348" if pass_rate >= 70 else ("#e67e22" if pass_rate >= 40 else "#b03a2e")

from collections import defaultdict
cat_counts = defaultdict(list)
for t in fail_traces:
    cat_counts[t[4]].append(t)

# ── Dimension scores (sample) ─────────────────────────────────────────────────
DIM_SCORES = [
    ("Task Completion",     0.78),
    ("Tool Selection",      0.71),
    ("Reasoning Coherence", 0.82),
    ("Policy Compliance",   0.94),
    ("Hallucination Risk",  0.55),
]

def bar(pct, color):
    return (
        f'<div style="background:#e8e8e8;border-radius:4px;height:10px;margin-top:4px;">'
        f'<div style="background:{color};width:{pct:.0f}%;height:10px;border-radius:4px;"></div>'
        f'</div>'
    )

def dim_color(v):
    if v < 0.5:  return "#b03a2e"
    if v < 0.75: return "#e67e22"
    return "#1d8348"

# ── Trace rows ────────────────────────────────────────────────────────────────
trace_rows = ""
for i, (task, verdict, score, status, cat, detail) in enumerate(TRACES, 1):
    bg = "#eafaf1" if status == "PASS" else "#fdf2f0"
    score_str = f"{score:.2f}"
    cat_str   = cat or "—"
    task_esc  = task[:80].replace("<","&lt;").replace(">","&gt;")
    trace_rows += (
        f'<tr style="background:{bg};">'
        f"<td>{i}</td><td>{task_esc}</td>"
        f'<td><strong style="color:{"#1d8348" if status=="PASS" else "#b03a2e"};">{status}</strong></td>'
        f"<td>{score_str}</td><td>{cat_str}</td></tr>"
    )

# ── Heatmap rows ──────────────────────────────────────────────────────────────
max_c = max(len(v) for v in cat_counts.values()) if cat_counts else 1
heatmap_rows = ""
for cat, group in sorted(cat_counts.items(), key=lambda x: -len(x[1])):
    pct = len(group) / len(fail_traces) * 100
    bw  = int(len(group) / max_c * 100)
    heatmap_rows += (
        f'<tr><td style="padding:8px 12px;font-weight:600;width:200px;">{cat}</td>'
        f'<td style="padding:8px 12px;width:50px;text-align:right;">{len(group)}</td>'
        f'<td style="padding:8px 12px;width:60px;text-align:right;">{pct:.0f}%</td>'
        f'<td style="padding:8px 12px;"><div style="background:#2e86de;height:18px;width:{bw}%;border-radius:3px;"></div></td></tr>'
    )

# ── RCA entries ───────────────────────────────────────────────────────────────
rca_html = ""
for cat, group in cat_counts.items():
    rca_html += f'<h3 style="color:#2e86de;margin:24px 0 8px;">{cat}</h3>'
    for task, _, score, _, _, detail in group:
        task_esc   = task.replace("<","&lt;").replace(">","&gt;")
        detail_esc = (detail or "").replace("<","&lt;").replace(">","&gt;")
        rca_html += f"""
        <div style="border:1px solid #e0e0e0;border-radius:6px;padding:16px;margin-bottom:14px;">
          <p style="margin:0 0 6px;"><strong>Task:</strong> {task_esc}</p>
          <p style="margin:0 0 6px;"><strong>Score:</strong> {score:.2f} &nbsp;|&nbsp; <strong>Verdict:</strong> FAIL</p>
          <p style="margin:0;"><strong>Detail:</strong> {detail_esc}</p>
        </div>"""

# ── Dimension scorecard HTML ──────────────────────────────────────────────────
dim_html = ""
for label, val in DIM_SCORES:
    color = dim_color(val)
    dim_html += f"""
    <div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;font-size:12pt;margin-bottom:4px;">
        <span style="font-weight:600;">{label}</span>
        <span style="font-weight:700;color:{color};">{val*100:.0f}%</span>
      </div>
      {bar(val*100, color)}
    </div>"""

# ── Recommendations ───────────────────────────────────────────────────────────
RECS = [
    ("Add retrieval-augmented generation (RAG) with source citations.",
     "3 of 7 failures were HALLUCINATION traced to the agent generating plausible but unverified clinical facts. "
     "Implement RAG that grounds every factual claim against your formulary and policy documents. "
     "Add a citation requirement to the system prompt. Target: all patient-facing responses within one sprint."),
    ("Fix tool-routing logic in the prescription-refill workflow.",
     "1 failure called the billing API instead of the formulary-check API — a routing error in the tool-selection layer. "
     "Add an explicit tool-selection rubric to the system prompt for prescription workflows. "
     "Unit-test the tool router against the 6 most common prescription task types."),
    ("Increase task-extraction completeness with explicit list-completion checks.",
     "1 failure stopped after extracting 3 of 7 required tasks from a multi-provider note. "
     "Add a self-check step: after initial extraction, prompt the agent to re-read the note and "
     "confirm no action items were missed before returning the final list."),
]
rec_cards = ""
for i, (title, body) in enumerate(RECS, 1):
    rec_cards += f"""
    <div style="display:flex;align-items:flex-start;gap:16px;border:1px solid #d6eaf8;
                border-radius:8px;padding:20px;margin-bottom:16px;background:#f0f8ff;">
      <div style="min-width:36px;height:36px;border-radius:50%;background:#2e86de;color:#fff;
                  font-size:18px;font-weight:700;display:flex;align-items:center;
                  justify-content:center;flex-shrink:0;">{i}</div>
      <div>
        <p style="margin:0 0 6px;font-weight:700;">{title}</p>
        <p style="margin:0;line-height:1.6;font-size:10.5pt;">{body}</p>
      </div>
    </div>"""

# ── Methodology section ───────────────────────────────────────────────────────
METHODOLOGY = """
<p>AgentEval evaluates each trace against five dimensions:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <thead><tr>
    <th style="background:#2e86de;color:#fff;padding:9px 12px;text-align:left;">Dimension</th>
    <th style="background:#2e86de;color:#fff;padding:9px 12px;text-align:left;">What We Measure</th>
  </tr></thead>
  <tbody>
    <tr style="background:#f0f7ff;"><td style="padding:8px 12px;font-weight:600;">Task Completion</td><td style="padding:8px 12px;">Did the agent successfully achieve the user's stated goal?</td></tr>
    <tr><td style="padding:8px 12px;font-weight:600;">Tool Selection</td><td style="padding:8px 12px;">Did the agent choose the correct tools and APIs for each step?</td></tr>
    <tr style="background:#f0f7ff;"><td style="padding:8px 12px;font-weight:600;">Reasoning Coherence</td><td style="padding:8px 12px;">Was the agent's chain-of-thought logical and internally consistent?</td></tr>
    <tr><td style="padding:8px 12px;font-weight:600;">Policy Compliance</td><td style="padding:8px 12px;">Did the agent stay within operational guidelines and safety constraints?</td></tr>
    <tr style="background:#f0f7ff;"><td style="padding:8px 12px;font-weight:600;">Hallucination Risk</td><td style="padding:8px 12px;">Did the agent fabricate facts, citations, or tool outputs?</td></tr>
  </tbody>
</table>
<p>Each dimension is scored 0.0–1.0 by the LLM judge. Traces scoring below 0.60 overall are flagged for human expert review.
Human verdict is the ground truth — it overrides the LLM verdict for all reporting purposes.</p>
"""

# ── Full HTML ─────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    margin: 2cm 2cm 2.5cm 2cm;
    @bottom-center {{
      content: "AgentEval · Agent Reliability Audit · {COMPANY} · SAMPLE — Not for distribution";
      font-size: 9pt; color: #888;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; color: #111; background: #fff; margin: 0; font-size: 11pt; line-height: 1.5; }}
  h1 {{ font-size: 28pt; font-weight: 700; margin: 0 0 12px; }}
  h2 {{ font-size: 16pt; font-weight: 700; color: #2e86de; margin: 0 0 16px; border-bottom: 2px solid #2e86de; padding-bottom: 6px; }}
  h3 {{ font-size: 13pt; font-weight: 700; margin: 0 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
  th {{ background: #2e86de; color: #fff; padding: 10px 12px; text-align: left; font-size: 10pt; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #e8e8e8; font-size: 10pt; vertical-align: top; }}
  .section {{ margin-bottom: 40px; }}
  .cover {{ text-align: center; padding: 120px 40px; page-break-after: always; }}
  .page-break {{ page-break-before: always; }}
  .sample-watermark {{
    position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%) rotate(-35deg);
    font-size: 72pt; font-weight: 900; color: rgba(46,134,222,0.06);
    white-space: nowrap; pointer-events: none; z-index: 0;
  }}
</style>
</head>
<body>
<div class="sample-watermark">SAMPLE REPORT</div>

<!-- PAGE 1: COVER -->
<div class="cover">
  <p style="font-size:11px;font-weight:700;letter-spacing:.1em;color:#2e86de;text-transform:uppercase;margin:0 0 16px;">Agent Reliability Audit</p>
  <h1>Agent Reliability Audit</h1>
  <p style="font-size:22pt;font-weight:700;color:#2e86de;margin:8px 0 8px;">{COMPANY}</p>
  <p style="font-size:11pt;color:#888;">Healthcare / Clinical AI · {REPORT_DATE}</p>
  <p style="font-size:10pt;color:#aaa;margin-top:8px;">Prepared by AgentEval &nbsp;·&nbsp; Confidential &nbsp;·&nbsp; SAMPLE</p>
  <div style="margin:48px auto 0;max-width:400px;border:1px solid #e0e0e0;border-radius:10px;padding:24px;">
    <p style="font-size:9pt;font-weight:700;letter-spacing:.08em;color:#888;text-transform:uppercase;margin:0 0 8px;">Report Contents</p>
    <p style="font-size:10pt;color:#374151;line-height:1.8;margin:0;">
      1. Executive Summary<br>
      2. Evaluation Methodology<br>
      3. Pass / Fail Results<br>
      4. Dimension Scorecard<br>
      5. Failure Heatmap<br>
      6. Root Cause Analysis<br>
      7. Top 3 Recommendations<br>
      8. Next Steps
    </p>
  </div>
</div>

<!-- PAGE 2: EXECUTIVE SUMMARY -->
<div class="section page-break">
  <h2>1. Executive Summary</h2>
  <div style="text-align:center;margin-bottom:28px;">
    <span style="font-size:60pt;font-weight:700;color:{pr_color};">{pass_rate:.0f}%</span>
    <p style="font-size:13pt;color:#555;margin:4px 0 0;">Overall Pass Rate</p>
  </div>
  <p>The agent demonstrated <strong>strong</strong> reliability across {total} evaluated traces, achieving a pass rate of {pass_rate:.1f}%.
  {pass_count} traces passed automated and human evaluation. {len(fail_traces)} traces were marked as failures.
  Failures were concentrated in hallucination risk and tool-selection accuracy — two dimensions that can be improved with targeted prompt engineering and retrieval-augmented generation.</p>
  <table style="margin-top:24px;">
    <thead><tr><th>Total Traces</th><th>Pass Rate</th><th>Failures</th><th>Human-Reviewed</th><th>Report Date</th></tr></thead>
    <tbody><tr>
      <td style="background:#fff;">{total}</td>
      <td style="background:#fff;color:{pr_color};font-weight:700;">{pass_rate:.1f}%</td>
      <td style="background:#fff;color:#b03a2e;">{len(fail_traces)}</td>
      <td style="background:#fff;">4</td>
      <td style="background:#fff;">{REPORT_DATE}</td>
    </tr></tbody>
  </table>
</div>

<!-- PAGE 3: METHODOLOGY -->
<div class="section page-break">
  <h2>2. Evaluation Methodology</h2>
  {METHODOLOGY}
  <h3 style="margin-top:24px;">Scoring Thresholds</h3>
  <table>
    <thead><tr><th>Overall Score</th><th>Verdict</th><th>Next Action</th></tr></thead>
    <tbody>
      <tr style="background:#eafaf1;"><td>≥ 0.75</td><td style="color:#1d8348;font-weight:700;">PASS</td><td>No action required</td></tr>
      <tr style="background:#fef9c3;"><td>0.55 – 0.74</td><td style="color:#92400e;font-weight:700;">UNCERTAIN</td><td>Escalated to human reviewer</td></tr>
      <tr style="background:#fdf2f0;"><td>&lt; 0.55</td><td style="color:#b03a2e;font-weight:700;">FAIL</td><td>Recorded as failure; included in RCA</td></tr>
    </tbody>
  </table>
</div>

<!-- PAGE 4: PASS/FAIL TABLE -->
<div class="section page-break">
  <h2>3. Pass / Fail Results</h2>
  <table>
    <thead><tr><th>#</th><th>Task</th><th>Verdict</th><th>Score</th><th>Category</th></tr></thead>
    <tbody>{trace_rows}</tbody>
  </table>
</div>

<!-- PAGE 5: DIMENSION SCORECARD -->
<div class="section page-break">
  <h2>4. Dimension Scorecard</h2>
  <p style="color:#555;margin-bottom:24px;">Average scores across all {total} traces, weighted by human-reviewed verdicts where available.</p>
  {dim_html}
  <p style="margin-top:24px;padding:16px;background:#fef9c3;border-radius:6px;font-size:10.5pt;">
    <strong>Weakest dimension: Hallucination Risk (55%).</strong>
    This is the primary driver of failures in this audit. See Root Cause Analysis for specific cases and the Recommendations section for fixes.
  </p>
</div>

<!-- PAGE 6: FAILURE HEATMAP -->
<div class="section page-break">
  <h2>5. Failure Heatmap</h2>
  <p style="color:#555;margin-bottom:16px;">Distribution of failure types across {len(fail_traces)} failed traces.</p>
  <table>
    <thead><tr><th>Category</th><th>Count</th><th>Share</th><th>Volume</th></tr></thead>
    <tbody>{heatmap_rows}</tbody>
  </table>
  <p style="margin-top:16px;font-size:10.5pt;color:#555;">
    <strong>HALLUCINATION</strong> is the dominant failure mode (3 of 7 failures, 43%), followed by
    <strong>INCOMPLETE</strong> task execution (2 of 7, 29%) and <strong>WRONG_TOOL</strong> selection (1 of 7, 14%).
  </p>
</div>

<!-- PAGE 7: ROOT CAUSE ANALYSIS -->
<div class="section page-break">
  <h2>6. Root Cause Analysis</h2>
  <p style="color:#555;margin-bottom:8px;">Per-failure breakdown grouped by failure category. Human reviewer notes included where applicable.</p>
  {rca_html}
</div>

<!-- PAGE 8: RECOMMENDATIONS -->
<div class="section page-break">
  <h2>7. Top 3 Recommendations</h2>
  <p style="color:#555;margin-bottom:20px;">Each recommendation is specific enough to be converted into an engineering ticket within one business day.</p>
  {rec_cards}
</div>

<!-- PAGE 9: NEXT STEPS -->
<div class="section page-break">
  <h2>8. Next Steps</h2>
  <p style="font-size:12pt;margin-bottom:12px;"><strong>Schedule your debrief call:</strong>
    <a href="{CALENDLY}" style="color:#2e86de;">{CALENDLY}</a></p>
  <p style="font-size:12pt;margin-bottom:24px;"><strong>Questions?</strong>
    <a href="mailto:hello@agenteval.com" style="color:#2e86de;">hello@agenteval.com</a></p>
  <p style="color:#888;font-size:10pt;border-top:1px solid #e0e0e0;padding-top:16px;">
    This is a <strong>sample report</strong> generated with anonymised synthetic data to illustrate the AgentEval report format.
    Your actual audit report will reflect your agent's real traces and will include domain-specific reviewer notes.
  </p>
</div>

</body>
</html>"""

os.makedirs("./static", exist_ok=True)
output = "./static/sample-report.pdf"
from weasyprint import HTML
HTML(string=html).write_pdf(output)
print(f"Sample report written to {output}")
