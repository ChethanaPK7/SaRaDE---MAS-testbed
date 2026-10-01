from rest_framework.routers import DefaultRouter

from .views import PostingViewSet

router = DefaultRouter()
router.register("", PostingViewSet, basename="posting")

urlpatterns = router.urls
