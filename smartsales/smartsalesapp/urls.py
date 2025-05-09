from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.home, name="dashboard"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("signup/", views.authView, name="signup"),

    path("request-reset/", views.request_reset, name="request_reset"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("set-new-password/", views.set_new_password, name="set_new_password"),

    path("products/", views.products_view, name="products"),

    path("add_product/", views.add_product_view, name="add_product"),

    path("delete-product/<int:product_id>/", views.delete_product_view, name="delete_product"),

    path("edit-product/<int:product_id>/", views.edit_product_view, name="edit_product"),
    path("record_transaction/", views.add_transaction_view, name="record_transaction"),
] + static(settings.STATIC_URL)