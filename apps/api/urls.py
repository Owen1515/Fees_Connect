"""API namespace; unsafe session requests require Django CSRF."""

from django.urls import path

from .views import ChatView, InvoiceListView, PaymentListView

app_name = "api"
urlpatterns = [
    path("support/chat/", ChatView.as_view(), name="chat"),
    path("payments/", PaymentListView.as_view(), name="payments"),
    path("invoices/", InvoiceListView.as_view(), name="invoices"),
]
