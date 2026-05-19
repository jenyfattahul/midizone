from django.contrib import admin
from django.urls import path
from dashboard import views  # Kita panggil file views.py dari aplikasi dashboard
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("admin/", admin.site.urls),
    # Path kosong '' artinya ini akan jadi halaman pertama yang muncul
    path("", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("input-lokasi/", views.input_lokasi, name="input_lokasi"),
    path("riwayat/", views.riwayat_view, name="riwayat"),
    ## ini buat road type
    path("road-feature/", views.road_feature_api, name="road_feature"),
    path("input-lokasi/simpan/", views.simpan_lokasi, name="simpan_lokasi"),
    path("download-pdf/<int:analysis_id>/", views.generate_pdf, name="download_pdf"),
    path("generate-pdf/<int:analysis_id>/", views.generate_pdf, name="generate_pdf"),
    path(
        "detail-riwayat/<int:analysis_id>/",
        views.detail_riwayat_partial,
        name="detail_riwayat",
    ),
]
