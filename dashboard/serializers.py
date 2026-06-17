from rest_framework import serializers
from .models import SiteAnalysis


class SiteAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteAnalysis
        fields = "__all__"
