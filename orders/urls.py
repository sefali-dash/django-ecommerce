from django.urls import path

from orders.views import OrderCancelView, OrderCreateListView, OrderDetailView

urlpatterns = [
    path("", OrderCreateListView.as_view(), name="order-list-create"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
]
