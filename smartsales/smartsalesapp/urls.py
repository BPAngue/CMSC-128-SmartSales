from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.home, name="home"),
    path("home/", views.home, name="home"),
    path("todos/", views.todos, name="Todos"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("signup/", views.authView, name="authView"),
] + static(settings.STATIC_URL)