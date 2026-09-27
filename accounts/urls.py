from django.urls import path
from . import views

urlpatterns = [
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/verify/", views.password_reset_verify, name="password_reset_verify"),
    path("password-reset/confirm/", views.password_reset_confirm_code, name="password_reset_confirm_code"),
]