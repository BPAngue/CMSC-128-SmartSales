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
] + static(settings.STATIC_URL)