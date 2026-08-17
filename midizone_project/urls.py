from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views
from dashboard import views
from django.contrib.auth import views as auth_views

# Teks Admin Header
admin.site.site_header = "SDSS Account Portal"
admin.site.site_title = "SDSS Portal"
admin.site.index_title = "Management Dashboard"

urlpatterns = [
    # 1. OVERRIDE RESET PASSWORD (Panggil template langsung dari folder templates/)
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",  # <-- Tanpa registration/
            success_url=reverse_lazy("login"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.LoginView.as_view(template_name="login.html"),
        name="password_reset_complete",
    ),
    # 2. Login & Logout Custom
    path("", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html")),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="login.html")),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    # 3. Include Auth Bawaan Django (Ditaruh DI BAWAH agar tidak menimpa override)
    path("", include("django.contrib.auth.urls")),
    # 4. Admin Panel
    path("admin/", admin.site.urls),
    # 5. Core Dashboard & Navigation
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("input-lokasi/", views.input_lokasi, name="input_lokasi"),
    path("riwayat/", views.riwayat_view, name="riwayat"),
    # 6. Analysis & API Endpoints
    path("api/site-analysis/", views.site_analysis_list),
    path("road-feature/", views.road_feature_api, name="road_feature"),
    path("input-lokasi/simpan/", views.simpan_lokasi, name="simpan_lokasi"),
    path(
        "detail-riwayat/<int:analysis_id>/",
        views.detail_riwayat_partial,
        name="detail_riwayat_partial",
    ),
    path("preview-pdf/<int:analysis_id>/", views.preview_pdf, name="preview_pdf"),
    path("generate-pdf/<int:analysis_id>/", views.generate_pdf, name="generate_pdf"),
    path("download-pdf/<int:analysis_id>/", views.generate_pdf, name="download_pdf"),
    path("download-pdf-bulk/", views.download_pdf_bulk, name="download_pdf_bulk"),
    path("hapus-riwayat-batch/", views.hapus_riwayat_batch, name="hapus_riwayat_batch"),
    path("api/password-reset/", views.password_reset_api, name="password_reset_api"),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
            # Arahkan success_url ke halaman login atau halaman khusus sukses
            success_url=reverse_lazy("login"),
        ),
        name="password_reset_confirm",
    ),
]
