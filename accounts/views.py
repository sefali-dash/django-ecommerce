from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.permissions import IsAdminUser
from accounts.serializers import (
    AdminUserListSerializer,
    AdminUserStatusSerializer,
    PasswordChangeSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from accounts.throttling import AuthRateThrottle

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)


class LoginView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    throttle_classes = (AuthRateThrottle,)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = (IsAuthenticated,)

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."})


class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = (IsAdminUser,)
    queryset = User.objects.all().order_by("-date_joined")


class AdminUserStatusView(generics.UpdateAPIView):
    serializer_class = AdminUserStatusSerializer
    permission_classes = (IsAdminUser,)
    queryset = User.objects.filter(is_staff=False)
    lookup_field = "pk"

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class AdminDashboardView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        from django.db.models import Sum

        from catalog.models import Category, Product
        from orders.models import Order

        total_revenue = (
            Order.objects.exclude(status=Order.Status.CANCELLED).aggregate(total=Sum("total_amount"))["total"]
            or 0
        )
        return Response(
            {
                "users_count": User.objects.count(),
                "categories_count": Category.objects.count(),
                "products_count": Product.objects.count(),
                "orders_count": Order.objects.count(),
                "total_revenue": str(total_revenue),
            }
        )
