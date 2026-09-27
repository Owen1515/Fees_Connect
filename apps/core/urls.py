"""Public FeesConnect pages."""

from django.urls import path
from django.views.generic import TemplateView

from .views import healthz, readyz

app_name = "core"
urlpatterns = [
    path("", TemplateView.as_view(template_name="feesconnect/index.html"), name="home"),
    path("demo/", TemplateView.as_view(template_name="feesconnect/demo.html"), name="demo"),
    path(
        "privacy/", TemplateView.as_view(template_name="feesconnect/privacy.html"), name="privacy"
    ),
    path("terms/", TemplateView.as_view(template_name="core/terms.html"), name="terms"),
    path("contact/", TemplateView.as_view(template_name="core/contact.html"), name="contact"),
    path("healthz/", healthz, name="healthz"),
    path("readyz/", readyz, name="readyz"),
]
