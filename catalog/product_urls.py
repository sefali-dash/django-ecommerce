from django.urls import path

from catalog.views import LowStockProductsView, ProductDetailView, ProductListCreateView

urlpatterns = [
    path("", ProductListCreateView.as_view(), name="product-list"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
]
