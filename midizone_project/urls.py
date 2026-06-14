from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from dashboard import views

urlpatterns = [
    # Admin Panel
    path("admin/", admin.site.urls),
    # Authentication
    path("", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    # Core Dashboard & Navigation
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("input-lokasi/", views.input_lokasi, name="input_lokasi"),
    path("riwayat/", views.riwayat_view, name="riwayat"),
    # Analysis & API Endpoints
    path("road-feature/", views.road_feature_api, name="road_feature"),
    path("input-lokasi/simpan/", views.simpan_lokasi, name="simpan_lokasi"),
    path('detail-riwayat/<int:analysis_id>/', views.detail_riwayat_partial, name='detail_riwayat_partial'),
    path('preview-pdf/<int:analysis_id>/', views.preview_pdf, name='preview_pdf'),
    # PDF Generation (Consolidated to single endpoint name)
    path("generate-pdf/<int:analysis_id>/", views.generate_pdf, name="generate_pdf"),
    # Kept for backward compatibility if specifically referenced in old templates
    path("download-pdf/<int:analysis_id>/", views.generate_pdf, name="download_pdf"),
    path("download-pdf-bulk/", views.download_pdf_bulk, name="download_pdf_bulk"),
    path("hapus-riwayat-batch/", views.hapus_riwayat_batch, name="hapus_riwayat_batch"),
]
