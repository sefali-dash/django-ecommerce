from django.urls import path

from catalog.views import CategoryDetailView, CategoryListCreateView

urlpatterns = [
    path("", CategoryListCreateView.as_view(), name="category-list"),
    path("<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
]
