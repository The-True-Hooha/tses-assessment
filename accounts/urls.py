from django.urls import path

from accounts.views import OTPRequestView, OTPVerifyView

urlpatterns = [
    path("otp/request", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify", OTPVerifyView.as_view(), name="otp-verify"),
]
