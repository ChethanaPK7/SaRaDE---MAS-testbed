from django.utils import timezone

from postings.models import InternshipPosting

from .llm import json_chat, chat


PROFILE_SYSTEM = """You are SaRaDE Profile Parser, a careful academic-profile extraction agent.
Extract only information explicitly present in the supplied text. Never invent grades,
papers, skills, institutions, dates or achievements. Return JSON with keys:
skills (array of strings), research_interests (array), education (array of objects),
projects (array), publications (array), experience (array), and summary (string).
"""

MATCH_SYSTEM = """You are SaRaDE Opportunity Matcher. Match a student's explicitly supplied
profile against research opportunities. Use only the supplied profile and postings.
Do not infer sensitive traits. Return JSON with a 'matches' array. Each match must
contain posting_id, title, score (0-100), reasons (array of short factual reasons),
and gaps (array of missing/uncertain qualifications). A score is a technical
compatibility estimate, not an admission probability or guarantee.
"""

SOP_SYSTEM = """You are SaRaDE SOP Writer. Draft a concise research-interest statement for a
student applying to a supplied research opportunity. Use only facts supplied by
the student. Do not invent achievements. Do not claim the student has skills they
have not provided. Make the result specific to the opportunity and transparent
about motivation. Return JSON with 'title', 'draft', and 'notes'.
"""


def parse_profile(text):
    return json_chat(
        PROFILE_SYSTEM,
        f"Extract the profile from this user-provided text:\n\n{text[:20000]}",
    )


def match_opportunities(profile, limit=12):
    qs = InternshipPosting.objects.select_related("institution").filter(
        is_active=True,
        application_deadline__gte=timezone.localdate(),
    )[:50]
    postings = [
        {
            "id": p.id,
            "title": p.title,
            "lab": p.lab,
            "institution": p.institution.name,
            "description": p.description,
            "eligibility": p.eligibility,
            "duration_weeks": p.duration_weeks,
            "stipend": p.stipend,
        }
        for p in qs
    ]
    result = json_chat(
        MATCH_SYSTEM,
        "STUDENT PROFILE:\n"
        + _compact_json(profile)
        + "\n\nOPEN OPPORTUNITIES:\n"
        + _compact_json(postings)
        + f"\n\nReturn at most {limit} matches, ordered by compatibility.",
    )
    result["matches"] = result.get("matches", [])[:limit]
    return result


def write_sop(profile, posting, constraints=""):
    prompt = (
        "STUDENT PROFILE:\n"
        + _compact_json(profile)
        + "\n\nTARGET OPPORTUNITY:\n"
        + _compact_json(posting)
        + "\n\nSTUDENT'S OPTIONAL CONSTRAINTS:\n"
        + constraints[:4000]
    )
    return json_chat(SOP_SYSTEM, prompt, temperature=0.4)


def _compact_json(value):
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

LEARNING_MAP_SYSTEM = """You are SaRaDE Learning Map Agent. Build a practical research-development map from
only the supplied student profile and target research opportunity. Do not invent coursework,
skills, publications, credentials or prerequisites as if they were facts. Clearly label
inferences/recommendations as recommendations. Return JSON with: target (string), current_strengths
(array), skill_gaps (array of objects with skill, why_needed, priority), learning_path (array of
objects with stage, topics, suggested_evidence), research_actions (array), and assumptions (array).
"""

VERIFIER_SYSTEM = """You are SaRaDE Verification Agent. Audit an agent-generated result against the supplied
source facts. Identify unsupported claims, contradictions, missing qualifications and unnecessary
personal-data exposure. Do not rewrite the source facts. Return JSON with: valid (boolean), issues
(array of objects with severity, field, explanation), supported_claims (array), and data_minimization
(array of fields that can be removed without harming the task).
"""


def build_learning_map(profile, posting):
    return json_chat(
        LEARNING_MAP_SYSTEM,
        "STUDENT PROFILE:\n" + _compact_json(profile) + "\n\nTARGET OPPORTUNITY:\n" + _compact_json(posting),
        temperature=0.2,
    )


def verify_result(source_profile, result, purpose="research-development"):
    return json_chat(
        VERIFIER_SYSTEM,
        "PURPOSE:\n" + purpose + "\n\nSOURCE PROFILE:\n" + _compact_json(source_profile)
        + "\n\nRESULT TO AUDIT:\n" + _compact_json(result),
        temperature=0.0,
    )
