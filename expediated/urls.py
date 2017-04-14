from django.urls import path, include
from .views import CustomerView, SendPrequalifyView

urlpatterns = [
    path('customer', CustomerView),
    path('send_prequalify', SendPrequalifyView),
]