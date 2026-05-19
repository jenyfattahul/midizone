from django.urls import path
from .views import road_feature_api

urlpatterns = [
    path("road-feature/", road_feature_api),
]
