"""Payment page and signed-provider callback namespace."""

from django.urls import path

from . import views, webhooks

app_name = "payments"
urlpatterns = [
    path("checkout/<uuid:invoice_id>/", views.checkout, name="checkout"),
    path("history/", views.history, name="history"),
    path("export/", views.export_history, name="export"),
    path("reconciliation/", views.reconciliation, name="reconciliation"),
    path("<uuid:pk>/", views.status, name="status"),
    path("<uuid:pk>/status/", views.status_json, name="status_json"),
    path("<uuid:pk>/receipt/", views.receipt, name="receipt"),
    path("<uuid:pk>/receipt/pdf/", views.receipt, {"pdf": True}, name="receipt_pdf"),
    path("<uuid:pk>/refund/", views.refund, name="refund"),
    path("webhooks/stripe/", webhooks.stripe_webhook, name="stripe_webhook"),
    path("webhooks/paypal/", webhooks.paypal_webhook, name="paypal_webhook"),
    path("webhooks/paynow/<uuid:merchant_id>/", webhooks.paynow_webhook, name="paynow_webhook"),
]
