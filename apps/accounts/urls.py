"""Named authentication routes and original-template compatibility aliases."""

from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "accounts"
urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path(
        "verification/sent/",
        TemplateView.as_view(template_name="accounts/verification_sent.html"),
        name="verification_sent",
    ),
    path(
        "verification/confirmed/",
        TemplateView.as_view(template_name="accounts/verification_confirmed.html"),
        name="verification_confirmed",
    ),
    path("verification/resend/", views.request_token, {"purpose": "verification"}, name="resend"),
    path("verify/<str:token>/", views.verify, name="verify"),
    path("password/reset/", views.request_token, name="reset_request"),
    path(
        "password/sent/",
        TemplateView.as_view(template_name="accounts/reset_sent.html"),
        name="reset_sent",
    ),
    path("password/reset/<str:token>/", views.reset_confirm, name="reset_confirm"),
    path(
        "password/complete/",
        TemplateView.as_view(template_name="accounts/reset_complete.html"),
        name="reset_complete",
    ),
    path("2fa/setup/", views.otp_setup, name="otp_setup"),
    path("2fa/verify/", views.otp_verify, name="otp_verify"),
    path("profile/", views.profile, name="profile"),
    path("password/change/", views.password_change, name="password_change"),
]
