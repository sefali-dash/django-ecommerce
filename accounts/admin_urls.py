from django.urls import path

from accounts.views import AdminDashboardView, AdminUserListView, AdminUserStatusView
from catalog.views import LowStockProductsView
from orders.views import AdminOrderListView, AdminOrderStatusView

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("users/", AdminUserListView.as_view(), name="admin-users-list"),
    path("users/<int:pk>/status/", AdminUserStatusView.as_view(), name="admin-users-status"),
    path("products/low-stock/", LowStockProductsView.as_view(), name="admin-products-low-stock"),
    path("orders/", AdminOrderListView.as_view(), name="admin-orders-list"),
    path("orders/<int:pk>/status/", AdminOrderStatusView.as_view(), name="admin-orders-status"),
]
