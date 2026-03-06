from config import settings


async def judge_trace(raw_json: str, agent_description: str) -> dict:
    """
    Send a trace to the LLM judge and return verdict, reasoning, and score.
    Returns a dict with keys: verdict, reasoning, score
    """
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = f"""You are an expert AI agent evaluator. Given the following agent description and conversation trace, evaluate the agent's performance.

Agent Description:
{agent_description}

Conversation Trace (JSON):
{raw_json}

Provide your evaluation in the following format:
VERDICT: PASS or FAIL
SCORE: (a float between 0.0 and 1.0)
REASONING: (detailed explanation of your verdict)
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    lines = response_text.strip().split("\n")

    verdict = None
    score = None
    reasoning_lines = []
    in_reasoning = False

    for line in lines:
        if line.startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip()
        elif line.startswith("SCORE:"):
            try:
                score = float(line.split(":", 1)[1].strip())
            except ValueError:
                score = None
        elif line.startswith("REASONING:"):
            in_reasoning = True
            reasoning_lines.append(line.split(":", 1)[1].strip())
        elif in_reasoning:
            reasoning_lines.append(line)

    return {
        "verdict": verdict,
        "score": score,
        "reasoning": "\n".join(reasoning_lines).strip(),
    }
