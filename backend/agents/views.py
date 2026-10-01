from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from postings.models import InternshipPosting

from .services import (
    build_learning_map,
    match_opportunities,
    parse_profile,
    verify_result,
    write_sop,
)
from .marl.orchestrator import plan as marl_plan
from .marl.orchestrator import state_from_context


class AgentCatalogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "environment": "SaRaDE Agent Environment",
            "coordination": {
                "algorithm": "QMIX",
                "training": "centralized training with decentralized execution (CTDE)",
                "fallback": "transparent rule-based coordinator",
                "consent_boundary": "Agents process only data explicitly supplied by the caller.",
            },
            "agents": [
                {"id": "profile-parser", "name": "AI Profile Parser", "description": "Extracts a structured research profile from supplied text."},
                {"id": "opportunity-matcher", "name": "Opportunity Matcher", "description": "Ranks open research opportunities by technical compatibility."},
                {"id": "learning-map", "name": "Learning Map Agent", "description": "Builds a research-development pathway and explicit skill-gap map."},
                {"id": "sop-writer", "name": "Student SOP Writer", "description": "Drafts an opportunity-specific research statement without inventing achievements."},
                {"id": "verification", "name": "Verification Agent", "description": "Audits generated outputs for unsupported claims and unnecessary data exposure."},
            ],
        })


class ProfileParserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if len(text) < 40:
            return Response({"detail": "Please provide at least 40 characters of profile/CV text."}, status=400)
        return Response(parse_profile(text))


class OpportunityMatcherView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.data.get("profile")
        if not isinstance(profile, dict):
            return Response({"detail": "profile must be a JSON object."}, status=400)
        try:
            limit = max(1, min(int(request.data.get("limit", 8)), 20))
        except (TypeError, ValueError):
            limit = 8
        return Response(match_opportunities(profile, limit=limit))


def _posting_payload(posting):
    return {
        "id": posting.id,
        "title": posting.title,
        "lab": posting.lab,
        "institution": posting.institution.name,
        "description": posting.description,
        "eligibility": posting.eligibility,
        "duration_weeks": posting.duration_weeks,
        "stipend": posting.stipend,
    }


def _get_posting(posting_id):
    try:
        return InternshipPosting.objects.select_related("institution").get(pk=posting_id)
    except InternshipPosting.DoesNotExist:
        return None


class LearningMapView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.data.get("profile")
        posting = _get_posting(request.data.get("posting_id"))
        if not isinstance(profile, dict) or not posting:
            return Response({"detail": "profile and a valid posting_id are required."}, status=400)
        return Response(build_learning_map(profile, _posting_payload(posting)))


class SOPWriterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.data.get("profile")
        posting = _get_posting(request.data.get("posting_id"))
        if not isinstance(profile, dict) or not posting:
            return Response({"detail": "profile and posting_id are required."}, status=400)
        constraints = (request.data.get("constraints") or "").strip()
        return Response(write_sop(profile, _posting_payload(posting), constraints=constraints))


class VerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.data.get("profile")
        result = request.data.get("result")
        if not isinstance(profile, dict) or result is None:
            return Response({"detail": "profile and result are required."}, status=400)
        return Response(verify_result(profile, result, request.data.get("purpose", "research-development")))


class CoordinationPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.data.get("profile") or {}
        matches = request.data.get("matches") or []
        learning_map = request.data.get("learning_map") or {}
        sop = request.data.get("sop") or {}
        consent_scope = request.data.get("consent_scope")
        state = state_from_context(profile, matches, learning_map, sop, consent_scope)
        plan = marl_plan(state)
        return Response({"state": state.tolist(), **plan})


class OrchestrateView(APIView):
    """One-shot agentic workflow driven by the learned coordinator.

    The coordinator decides which stages to request; it does not get direct access
    to lockers or credentials. The caller controls the data supplied to each stage.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = request.data.get("profile")
        posting_id = request.data.get("posting_id")
        if not isinstance(profile, dict) or not posting_id:
            return Response({"detail": "profile and posting_id are required."}, status=400)
        posting = _get_posting(posting_id)
        if not posting:
            return Response({"detail": "Opportunity not found."}, status=404)
        posting_data = _posting_payload(posting)

        matches = request.data.get("matches") or []
        learning_map = request.data.get("learning_map") or {}
        sop = request.data.get("sop") or {}
        consent_scope = request.data.get("consent_scope")
        coordination = marl_plan(state_from_context(profile, matches, learning_map, sop, consent_scope))
        selected = set(coordination["selected_agents"])
        outputs = {}

        # Explicitly map coordinator actions to callable stages.
        if "profile" in selected and not profile.get("skills"):
            outputs["profile"] = {"action": "profile data already supplied", "skipped": True}
        if "matcher" in selected:
            outputs["matches"] = match_opportunities(profile, limit=8)
        if "learning_map" in selected:
            outputs["learning_map"] = build_learning_map(profile, posting_data)
        if "sop" in selected:
            outputs["sop"] = write_sop(profile, posting_data, request.data.get("constraints", ""))

        verification = None
        if request.data.get("verify", True) and outputs:
            verification = verify_result(profile, outputs)

        return Response({
            "coordination": coordination,
            "outputs": outputs,
            "verification": verification,
            "data_boundary": "Only explicitly supplied request data was sent to agents; no Anumati locker was read by the coordinator.",
        })
