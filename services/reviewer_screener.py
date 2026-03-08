"""Reviewer screening service.

Handles quiz generation, scoring, and trial assignment for reviewer candidates.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from models import ReviewerProfile, ReviewerQuiz


def generate_quiz(reviewer_id: str, domain: str, db: Session) -> ReviewerQuiz:
    """Create a domain quiz for a reviewer candidate."""
    import json
    import uuid

    questions = _get_questions_for_domain(domain)
    quiz = ReviewerQuiz(
        id=str(uuid.uuid4()),
        reviewer_id=reviewer_id,
        domain=domain,
        questions=json.dumps(questions),
        status="PENDING",
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def score_quiz(quiz_id: str, answers: dict, db: Session) -> float:
    """Score submitted quiz answers and update the reviewer's quiz_score."""
    import json
    from datetime import datetime

    quiz = db.query(ReviewerQuiz).filter(ReviewerQuiz.id == quiz_id).first()
    if not quiz:
        raise ValueError(f"Quiz {quiz_id} not found")

    questions = json.loads(quiz.questions)
    correct = sum(
        1 for q in questions
        if answers.get(q["id"]) == q.get("answer")
    )
    score = round(correct / len(questions) * 100, 1) if questions else 0.0

    quiz.answers = json.dumps(answers)
    quiz.score = score
    quiz.status = "SUBMITTED"
    quiz.submitted_at = datetime.utcnow()

    reviewer = db.query(ReviewerProfile).filter(ReviewerProfile.id == quiz.reviewer_id).first()
    if reviewer:
        reviewer.quiz_score = score
        reviewer.quiz_submitted_at = datetime.utcnow()

    db.commit()
    return score


def _get_questions_for_domain(domain: str) -> list[dict]:
    """Return a basic question set for the given domain."""
    return [
        {
            "id": "q1",
            "text": f"In {domain} agent evaluation, what does a PASS verdict indicate?",
            "options": [
                "The agent completed the task correctly and safely",
                "The agent attempted the task",
                "The agent produced any output",
                "The agent used tools",
            ],
            "answer": "The agent completed the task correctly and safely",
        },
        {
            "id": "q2",
            "text": "Which failure category best describes an agent inventing facts not in its context?",
            "options": ["HALLUCINATION", "INCOMPLETE", "WRONG_TOOL", "LOOP"],
            "answer": "HALLUCINATION",
        },
        {
            "id": "q3",
            "text": "An agent calls the same tool 10 times with identical inputs. This is best categorized as:",
            "options": ["LOOP", "HALLUCINATION", "WRONG_TOOL", "INCOMPLETE"],
            "answer": "LOOP",
        },
    ]
