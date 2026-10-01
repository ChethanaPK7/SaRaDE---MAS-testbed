from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({"status": "ok", "service": "srip-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("users.urls")),
    path("api/postings/", include("postings.urls")),
    path("api/applications/", include("applications.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/anumati/", include("anumati_integration.urls")),
    path("api/agents/", include("agents.urls")),
]
