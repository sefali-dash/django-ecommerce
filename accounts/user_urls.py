from django.urls import path

from accounts.views import MeView, PasswordChangeView

urlpatterns = [
    path("me/", MeView.as_view(), name="users-me"),
    path("me/password/", PasswordChangeView.as_view(), name="users-me-password"),
]
