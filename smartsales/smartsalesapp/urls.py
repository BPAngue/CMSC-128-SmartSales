from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name="home"),
    path("home/", views.home, name="home_alt"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("signup/", views.authView, name="signup"),

    # OTP based password reset flow
    path("request-reset/", views.request_reset, name="request_reset"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("set-new-password/", views.set_new_password, name="set_new_password"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
] + static(settings.STATIC_URL)