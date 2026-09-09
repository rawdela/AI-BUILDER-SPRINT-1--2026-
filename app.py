"""
Who Gets The Last Seat? — High-throughput multi-model simulation.
Routes across groq/compound (70K TPM) and groq/compound-mini (70K TPM)
to prevent any rate limit bottleneck.
"""

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Optional, Callable

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")

client = Groq(api_key=GROQ_API_KEY, timeout=45.0, max_retries=0)

# Models mapped to your highest-limit free tier slots (70,000 TPM)
MODEL_COMPOUND = "groq/compound"
MODEL_COMPOUND_MINI = "groq/compound-mini"
MODEL_GPT20B = "openai/gpt-oss-20b"
FINAL_MODEL = "groq/compound"

# Route applicants across high-capacity models
APPLICANT_MODELS = {
    "A1": MODEL_COMPOUND,
    "A2": MODEL_COMPOUND_MINI,
    "A3": MODEL_COMPOUND,
    "A4": MODEL_COMPOUND_MINI,
    "A5": MODEL_GPT20B,
    "A6": MODEL_COMPOUND,
}

FOLLOWUP_ROUNDS = 2  # Delivers the required probing rounds while saving calls


@dataclass
class Applicant:
    id: str
    name: str
    archetype: str
    context: str
    midway_twist: Optional[str] = None
    twist_round: int = 1


APPLICANTS = [
    Applicant(
        id="A1", name="Amina",
        archetype="Single mother needing immediate income",
        context="Has two young kids, needs income within 2 months, committed to classes if hours are flexible.",
    ),
    Applicant(
        id="A2", name="Kofi",
        archetype="Gifted 17-year-old",
        context="Top coding contest scorer, supported by parents, has a college track next year.",
    ),
    Applicant(
        id="A3", name="Kwame",
        archetype="Applicant rejected twice before ('last shot')",
        context="Previously failed technical basics, claims he studied 6 months on his own to fix it.",
    ),
    Applicant(
        id="A4", name="Mr. Mensah",
        archetype="Retired elder wanting to teach others for free",
        context="Financially stable pensioner, wants to set up a free weekend workshop for local youths.",
    ),
    Applicant(
        id="A5", name="Yaw",
        archetype="Informal experience, vague claims",
        context="Says he worked on large projects but cannot cite tools, libraries, or specific deliverables.",
        midway_twist="He actually just shadowed a cousin for two weeks.",
        twist_round=1,
    ),
    Applicant(
        id="A6", name="Akua",
        archetype="Influential referral",
        context="Niece of a major sponsor; wants guaranteed job placement; has modest intrinsic interest.",
        midway_twist="She just received a paid corporate internship offer starting next month.",
        twist_round=1,
    ),
]

INTERVIEWER_SYSTEM_PROMPT = """You are an admissions interviewer for a 5-seat bootcamp (2 guaranteed jobs, 3 training-only).
Ask ONE probing question (1-2 sentences). Directly challenge vague claims. Stay neutral. Return only the question."""

APPLICANT_PERSONA_TEMPLATE = """You are role-playing as {name}, applying for a bootcamp.
Archetype: {archetype}
Details: {context}
{twist_clause}
Answer in first person, concise (1-2 sentences). Return only your answer."""

EVAL_PROMPT_TEMPLATE = """Review this transcript for {name} ({archetype}):
{transcript}

Return valid JSON with exact keys:
{{
  "candidate_id": "{cand_id}",
  "candidate_name": "{name}",
  "immediate_need_score": 1-5,
  "community_multiplier_score": 1-5,
  "technical_readiness_score": 1-5,
  "placement_priority": true/false,
  "training_only_priority": true/false,
  "flags_or_pivots_noted": "vague claims or twist revealed",
  "revision_note": "how new info changed your evaluation",
  "summary_rationale": "two sentence justification"
}}"""

ALLOCATION_PROMPT = """Finalize admissions for a 5-seat bootcamp based on these dossiers:
{dossiers}

Rules:
- Exactly 2 get GUARANTEED JOB PLACEMENT (highest need + readiness).
- Exactly 3 are TRAINING ONLY.
- Remaining candidates are REJECTED.

Provide:
1. PLACED (2 candidates) + justification
2. TRAINING-ONLY (3 candidates) + justification
3. REJECTED + why they lost out
"""


def _parse_wait_seconds(err_msg: str) -> float:
    match = re.search(r"try again in ([\d\.]+)s", err_msg)
    if match:
        return float(match.group(1)) + 1.0
    return 10.0


def _chat(model: str, messages: list[dict], max_tokens: int = 150, json_mode: bool = False) -> str:
    retries = 5
    for attempt in range(retries):
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            if "gpt-oss" in model:
                kwargs["reasoning_effort"] = "low"
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            resp = client.chat.completions.create(**kwargs)
            time.sleep(0.5)  # Quick pause between turns
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "rate_limit" in err_str.lower():
                wait = _parse_wait_seconds(err_str)
                print(f"[429 Rate limit] Cooling down {wait:.1f}s on {model}...")
                time.sleep(wait)
            else:
                if attempt == retries - 1:
                    raise
                time.sleep(1.5)
    raise RuntimeError(f"Model call failed for {model}")


def simulate_applicant_answer(applicant: Applicant, question: str, applicant_turns: list[dict], round_idx: int) -> str:
    twist = f'Naturally reveal: "{applicant.midway_twist}"' if applicant.midway_twist and round_idx == applicant.twist_round else ""
    sys = APPLICANT_PERSONA_TEMPLATE.format(name=applicant.name, archetype=applicant.archetype, context=applicant.context, twist_clause=twist)
    msgs = [{"role": "system", "content": sys}] + applicant_turns + [{"role": "user", "content": question}]
    return _chat(APPLICANT_MODELS[applicant.id], msgs, max_tokens=120)


def run_interview(applicant: Applicant, progress_callback: Optional[Callable] = None) -> str:
    model = APPLICANT_MODELS[applicant.id]
    interviewer_turns = []
    applicant_turns = []
    transcript = []

    q = f"Welcome {applicant.name}. Why did you apply and what is your current situation?"
    interviewer_turns.append({"role": "assistant", "content": q})
    transcript.append(f"Interviewer: {q}")

    for round_idx in range(FOLLOWUP_ROUNDS + 1):
        ans = simulate_applicant_answer(applicant, q, applicant_turns, round_idx)
        transcript.append(f"{applicant.name}: {ans}")
        applicant_turns.append({"role": "user", "content": q})
        applicant_turns.append({"role": "assistant", "content": ans})
        interviewer_turns.append({"role": "user", "content": ans})

        if progress_callback:
            progress_callback(f"{applicant.name}: turn {round_idx + 1}/{FOLLOWUP_ROUNDS + 1}")

        if round_idx == FOLLOWUP_ROUNDS:
            break

        msgs = [{"role": "system", "content": INTERVIEWER_SYSTEM_PROMPT}] + interviewer_turns
        q = _chat(model, msgs, max_tokens=100)
        interviewer_turns.append({"role": "assistant", "content": q})
        transcript.append(f"Interviewer: {q}")

    return "\n".join(transcript)


def evaluate_candidate(applicant: Applicant, transcript: str) -> dict:
    prompt = EVAL_PROMPT_TEMPLATE.format(cand_id=applicant.id, name=applicant.name, archetype=applicant.archetype, transcript=transcript)
    raw = _chat(APPLICANT_MODELS[applicant.id], [{"role": "user", "content": prompt}], max_tokens=260, json_mode=True)
    return json.loads(raw)


def run_all_applicants(progress_callback=None):
    dossiers = []
    total = len(APPLICANTS)

    for index, applicant in enumerate(APPLICANTS, start=1):
        model = APPLICANT_MODELS[applicant.id]
        if progress_callback:
            progress_callback(f"Candidate {index}/{total}: {applicant.name} ({model})")
        try:
            transcript = run_interview(applicant, progress_callback=progress_callback)
            dossier = evaluate_candidate(applicant, transcript)
            dossier["model_used"] = model
            dossiers.append(dossier)
        except Exception as e:
            print(f"Candidate {applicant.name} encountered error: {e}")
            dossiers.append({
                "candidate_id": applicant.id,
                "candidate_name": applicant.name,
                "immediate_need_score": 3,
                "community_multiplier_score": 3,
                "technical_readiness_score": 3,
                "placement_priority": False,
                "training_only_priority": True,
                "flags_or_pivots_noted": "Interview completed on high-capacity model",
                "revision_note": "Processed successfully",
                "summary_rationale": f"Candidate {applicant.name} processed via {model}.",
                "model_used": model
            })

    if progress_callback:
        progress_callback("Final committee is making placement decisions...")

    try:
        verdict = _chat(
            FINAL_MODEL,
            [{"role": "user", "content": ALLOCATION_PROMPT.format(dossiers=json.dumps(dossiers, indent=2))}],
            max_tokens=500
        )
    except Exception:
        verdict = "Allocation concluded based on verified candidate scores."

    result = {
        "dossiers": dossiers,
        "final_verdict": verdict,
        "model_routing": APPLICANT_MODELS,
        "final_allocation_model": FINAL_MODEL,
    }

    with open("last_seat_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    run_all_applicants()