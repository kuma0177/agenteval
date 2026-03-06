import json

import anthropic

from config import settings
from models import EvalStatus, Job, JobStatus, ReviewerToken, Trace


def evaluate_trace(trace, db_session) -> dict:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    result = {}
    verdict = "UNCERTAIN"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=(
                "You are an expert AI agent evaluator. Assess whether the agent "
                "successfully completed its assigned task. Return a structured verdict."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"TASK: {trace.outcome}\n"
                        f"TRACE: {trace.raw_json}\n\n"
                        "Return ONLY valid JSON with exactly these fields:\n"
                        "{\n"
                        '  "verdict": "PASS" | "FAIL" | "UNCERTAIN",\n'
                        '  "score": 0.0 to 1.0,\n'
                        '  "reasoning": "2-3 sentences explaining the verdict",\n'
                        '  "failure_category": null | "WRONG_TOOL" | "HALLUCINATION" | '
                        '"INCOMPLETE" | "POLICY_VIOLATION" | "LOOP" | "OTHER",\n'
                        '  "failure_detail": null | "one sentence on the specific failure"\n'
                        "}\n"
                        "No markdown, no code fences. Just the JSON object."
                    ),
                }
            ],
        )

        raw_text = response.content[0].text.strip()
        # Strip markdown code fences if the model wraps anyway
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        result = json.loads(raw_text)
        verdict = result.get("verdict", "UNCERTAIN")
        if verdict not in ("PASS", "FAIL", "UNCERTAIN"):
            verdict = "UNCERTAIN"

    except Exception:
        verdict = "UNCERTAIN"
        result = {
            "verdict": "UNCERTAIN",
            "score": 0.0,
            "reasoning": "Failed to parse LLM response.",
            "failure_category": None,
            "failure_detail": None,
        }

    status_map = {
        "PASS": EvalStatus.PASS,
        "FAIL": EvalStatus.FAIL,
        "UNCERTAIN": EvalStatus.NEEDS_REVIEW,
    }

    trace.llm_verdict = verdict
    trace.llm_score = result.get("score")
    trace.llm_reasoning = result.get("reasoning")
    trace.failure_category = result.get("failure_category")
    trace.failure_detail = result.get("failure_detail")
    trace.eval_status = status_map[verdict]
    db_session.commit()

    return result


def evaluate_job(job_id: str, db_session) -> list:
    job = db_session.query(Job).filter(Job.id == job_id).first()
    if not job:
        return []

    pending_traces = (
        db_session.query(Trace)
        .filter(Trace.job_id == job_id, Trace.eval_status == EvalStatus.PENDING)
        .all()
    )

    job.status = JobStatus.EVALUATING
    db_session.commit()

    for trace in pending_traces:
        evaluate_trace(trace, db_session)

    job.status = JobStatus.REVIEW
    db_session.commit()

    needs_review = (
        db_session.query(Trace)
        .filter(Trace.job_id == job_id, Trace.eval_status == EvalStatus.NEEDS_REVIEW)
        .all()
    )

    token_pairs = []
    for trace in needs_review:
        rt = ReviewerToken(trace_id=trace.id)
        db_session.add(rt)
        db_session.flush()
        token_pairs.append((trace.id, rt.token))

    db_session.commit()
    return token_pairs
