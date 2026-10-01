from django.urls import path

from .views import (
    AgentCatalogView,
    CoordinationPlanView,
    LearningMapView,
    OpportunityMatcherView,
    OrchestrateView,
    ProfileParserView,
    SOPWriterView,
    VerificationView,
)

urlpatterns = [
    path("", AgentCatalogView.as_view(), name="agent-catalog"),
    path("profile-parser/", ProfileParserView.as_view(), name="profile-parser"),
    path("opportunity-matcher/", OpportunityMatcherView.as_view(), name="opportunity-matcher"),
    path("learning-map/", LearningMapView.as_view(), name="learning-map"),
    path("sop-writer/", SOPWriterView.as_view(), name="sop-writer"),
    path("verify/", VerificationView.as_view(), name="verify-agent-output"),
    path("coordination-plan/", CoordinationPlanView.as_view(), name="coordination-plan"),
    path("orchestrate/", OrchestrateView.as_view(), name="orchestrate"),
]
