from django.db import models
from django.contrib.auth.models import User
from datetime import date


# 1. TABEL MASTER LOCATION
class Location(models.Model):
    location_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="locations")
    latitude = models.FloatField()
    longitude = models.FloatField()
    h3_index = models.CharField(
        max_length=15, blank=True, null=True
    )  # Tambahan H3 Index
    address = models.TextField()

    # Tambahkan fungsi ini di bawah field address
    def get_formatted_address(self):
        parts = [p.strip() for p in self.address.split(",")]
        # Logika: Jika formatnya [Jalan, Provinsi, Kota], ubah jadi [Jalan, Kota, Provinsi]
        if len(parts) >= 3:
            return f"{parts[0]}, {parts[2]}, {parts[1]}"
        return self.address

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        return f"Loc {self.location_id} - ({self.latitude}, {self.longitude})"


# 2. TABEL SITE ANALYSIS
class SiteAnalysis(models.Model):
    analysis_id = models.AutoField(primary_key=True)
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="site_analyses"
    )
    road_type = models.CharField(max_length=100)
    intersection_count = models.IntegerField(default=0)  # Tambahan fitur spasial
    region = models.CharField(max_length=50, default="lainnya")  # Klaster ML Zona
    input_date = models.DateTimeField(auto_now_add=True)
    nomor_dokumen = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "Site Analysis"
        verbose_name_plural = "Site Analyses"
        ordering = ["-input_date"]

    def save(self, *args, **kwargs):
        if not self.nomor_dokumen:
            # NOTE: count() can lead to race conditions in high-concurrency environments.
            count = SiteAnalysis.objects.count() + 1
            # Format: DOC/2026/001
            self.nomor_dokumen = f"DOC/{date.today().year}/{count:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Analysis {self.analysis_id}"


# 3. TABEL ANALYSIS POPULATION
class AnalysisPopulation(models.Model):
    population_id = models.AutoField(primary_key=True)
    analysis = models.ForeignKey(
        SiteAnalysis, on_delete=models.CASCADE, related_name="populations"
    )
    population_density = models.FloatField()
    population_2020 = models.IntegerField(default=0)
    population_2026 = models.IntegerField(default=0)
    population_category = models.CharField(max_length=50, default="low")
    data_source = models.CharField(max_length=100, default="WorldPop")

    class Meta:
        verbose_name = "Analysis Population"
        verbose_name_plural = "Analysis Populations"


# 4. TABEL ANALYSIS SNAPSHOT (POI & COMPETITOR AGGREGATE)
class AnalysisSnapshot(models.Model):
    snapshot_id = models.AutoField(primary_key=True)
    analysis = models.ForeignKey(
        SiteAnalysis, on_delete=models.CASCADE, related_name="snapshots"
    )
    # Fitur POI Cacahan Gambar 4 & 6
    restaurant_count = models.IntegerField(default=0)
    school_count = models.IntegerField(default=0)
    bank_count = models.IntegerField(default=0)
    hospital_count = models.IntegerField(default=0)
    total_poi = models.IntegerField(default=0)
    # Fitur Kompetitor Market
    supermarket_count = models.IntegerField(default=0)
    other_minimarket_count = models.IntegerField(default=0)
    alfamidi_count = models.IntegerField(default=0)
    total_competitor = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Analysis Snapshot"
        verbose_name_plural = "Analysis Snapshots"


# 5. TABEL MODEL RESULT
class ModelResult(models.Model):
    result_id = models.AutoField(primary_key=True)
    analysis = models.ForeignKey(
        SiteAnalysis, on_delete=models.CASCADE, related_name="results"
    )
    feasibility_prediction = models.CharField(max_length=50, default="LAYAK")
    confidence_score = models.FloatField(default=87.0)
    traffic_score_prediction = models.FloatField(default=0.0)
    traffic_category_prediction = models.CharField(
        max_length=50, default="Low"
    )  # Output Low/Med/High
    pdf_link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Model Result"
        verbose_name_plural = "Model Results"
