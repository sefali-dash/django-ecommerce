from django.db.models import ProtectedError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from accounts.permissions import IsAdminUser
from catalog.filters import ProductFilter
from catalog.models import Category, Product
from catalog.serializers import CategorySerializer, ProductSerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "pk"

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.products.exists():
            return Response(
                {"detail": "Cannot delete category while products still reference it."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Cannot delete category while products still reference it."},
                status=status.HTTP_409_CONFLICT,
            )


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    search_fields = ("name", "description")
    ordering_fields = ("price", "created_at", "name")
    ordering = ("-created_at",)

    def get_queryset(self):
        qs = Product.objects.select_related("category").all()
        if self.request.method == "GET" and not getattr(self.request.user, "is_staff", False):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    lookup_field = "pk"

    def get_queryset(self):
        qs = Product.objects.select_related("category").all()
        if self.request.method == "GET" and not getattr(self.request.user, "is_staff", False):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class LowStockProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        from django.conf import settings

        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        return Product.objects.filter(stock_quantity__lte=threshold, is_active=True).select_related(
            "category"
        )
