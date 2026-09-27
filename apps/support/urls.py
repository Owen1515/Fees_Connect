"""Support namespace."""

from django.urls import path

from . import views

app_name = "support"
urlpatterns = [path("", views.home, name="home"), path("<uuid:pk>/", views.detail, name="ticket")]
