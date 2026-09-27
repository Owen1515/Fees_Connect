"""School and billing URL namespace."""

from django.urls import path

from . import views

app_name = "fees"
urlpatterns = [
    path("", views.invoice_list, name="list"),
    path("students/register/", views.student_register, name="student_register"),
    path("schools/register/", views.school_register, name="school_register"),
    path("schools/manage/", views.school_workspace, name="school_workspace"),
    path("invoices/new/", views.issue_invoice, name="issue_invoice"),
    path("invoices/<uuid:pk>/", views.invoice_detail, name="invoice"),
    path("invoices/<uuid:pk>/pdf/", views.invoice_detail, {"pdf": True}, name="invoice_pdf"),
]
