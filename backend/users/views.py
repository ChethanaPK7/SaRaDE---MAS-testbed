from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Institution
from .serializers import InstitutionSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Public sign-up. Returns JWT tokens along with the created user so the
    frontend can log the user straight in after registering."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=201,
        )


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class InstitutionListView(generics.ListCreateAPIView):
    """List institutions (for the sign-up form's dropdown). Creating a new
    institution is open to any authenticated user in Phase 1 for demo
    convenience; lock this down before production."""

    queryset = Institution.objects.all().order_by("name")
    serializer_class = InstitutionSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
