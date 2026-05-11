from django.contrib import admin
from django.urls import path
from dashboard import views  # Kita panggil file views.py dari aplikasi dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    # Path kosong '' artinya ini akan jadi halaman pertama yang muncul
    path("", views.login_view, name="login"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("input-lokasi/", views.input_lokasi, name="input_lokasi"),
    path("riwayat/", views.riwayat_view, name="riwayat"),
]
