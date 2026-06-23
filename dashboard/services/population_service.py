import os
import math
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point, box
from rasterio.mask import mask
from pyproj import Transformer

# =========================
# LOAD RASTER
# =========================
raster_path = os.path.join(
    os.path.dirname(__file__),
    "../../data/idn_pd_2020_1km_UNadj.tif"
)

src = rasterio.open(raster_path)
raster_bounds = box(*src.bounds)

# =========================
# TRANSFORMER
# =========================
to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

# =========================
# GROWTH RATE PER PROVINSI (BPS SENSUS 2010 & 2020)
# Sumber: BPS Sensus Penduduk 2010 dan 2020
# CAGR = (P_2020 / P_2010)^(1/10) - 1
# =========================
PROVINCE_GROWTH = {
    "DKI Jakarta":          (9607787,    10562088,    0.00964),
    "Jawa Barat":           (43021826,   48274162,    0.01163),
    "Jawa Tengah":          (32380687,   36516035,    0.01202),
    "DI Yogyakarta":        (3457491,    3668719,     0.00594),
    "Jawa Timur":           (37476757,   40665696,    0.00824),
    "Banten":               (10632166,   11904562,    0.01145),
    "Aceh":                 (4486570,    5274871,     0.01627),
    "Sumatera Utara":       (12982204,   14799361,    0.01312),
    "Sumatera Barat":       (4846909,    5534472,     0.01335),
    "Riau":                 (5538367,    6394087,     0.01446),
    "Kepulauan Riau":       (1679163,    2064564,     0.02083),
    "Jambi":                (3092265,    3548228,     0.01381),
    "Sumatera Selatan":     (7450394,    8467432,     0.01290),
    "Bangka Belitung":      (1223048,    1455678,     0.01749),
    "Bengkulu":             (1715518,    2010670,     0.01594),
    "Lampung":              (7608405,    9007848,     0.01700),
    "Kalimantan Barat":     (4393239,    5414390,     0.02101),
    "Kalimantan Tengah":    (2212089,    2669969,     0.01886),
    "Kalimantan Selatan":   (3626119,    4215857,     0.01513),
    "Kalimantan Timur":     (3553143,    3766039,     0.00584),
    "Kalimantan Utara":     (525897,     701814,      0.02921),
    "Sulawesi Utara":       (2270596,    2621923,     0.01449),
    "Gorontalo":            (1040164,    1171681,     0.01193),
    "Sulawesi Tengah":      (2635009,    3022866,     0.01385),
    "Sulawesi Selatan":     (8032551,    9073509,     0.01228),
    "Sulawesi Barat":       (1158651,    1419229,     0.02038),
    "Sulawesi Tenggara":    (2232586,    2624880,     0.01635),
    "Nusa Tenggara Barat":  (4500212,    5320092,     0.01695),
    "Nusa Tenggara Timur":  (4683827,    5325566,     0.01294),
    "Bali":                 (3890757,    4317404,     0.01046),
    "Maluku":               (1533506,    1848923,     0.01888),
    "Maluku Utara":         (1038087,    1282937,     0.02134),
    "Papua":                (2833381,    4303707,     0.04265),
    "Papua Barat":          (760422,     1134068,     0.04070),
}

# Bounding box per provinsi untuk lookup koordinat → provinsi
# Format: (lat_min, lat_max, lon_min, lon_max)
PROVINCE_BOUNDS = {
    "DKI Jakarta":          (-6.37,  -6.10, 106.65, 107.00),
    "Jawa Barat":           (-7.82,  -5.89, 105.17, 108.81),
    "Banten":               (-7.08,  -5.88, 105.17, 106.72),
    "Jawa Tengah":          (-8.25,  -5.90, 108.05, 111.70),
    "DI Yogyakarta":        (-8.19,  -7.60, 110.03, 110.82),
    "Jawa Timur":           (-8.96,  -6.85, 110.75, 115.75),
    "Bali":                 (-8.85,  -8.05, 114.43, 115.72),
    "Nusa Tenggara Barat":  (-9.08,  -8.07, 115.75, 119.00),
    "Nusa Tenggara Timur":  (-11.02, -8.07, 118.97, 125.52),
    "Aceh":                 (2.00,    5.90,  94.97,  98.48),
    "Sumatera Utara":       (1.15,    4.45,  97.10, 100.40),
    "Sumatera Barat":       (-3.50,   1.10,  98.20, 101.80),
    "Riau":                 (-0.25,   2.70, 100.00, 104.10),
    "Kepulauan Riau":       (-0.60,   4.30, 103.55, 108.90),
    "Jambi":                (-2.50,   0.20, 101.40, 104.60),
    "Sumatera Selatan":     (-5.85,  -1.30, 102.20, 106.40),
    "Bangka Belitung":      (-3.50,  -1.00, 105.05, 108.60),
    "Bengkulu":             (-5.52,  -2.15, 101.05, 103.78),
    "Lampung":              (-5.93,  -3.72, 103.58, 105.93),
    "Kalimantan Barat":     (-3.10,   2.10, 108.00, 117.80),
    "Kalimantan Tengah":    (-4.40,  -0.10, 110.80, 116.60),
    "Kalimantan Selatan":   (-4.70,  -1.30, 114.50, 117.50),
    "Kalimantan Timur":     (-4.00,   2.70, 113.70, 119.00),
    "Kalimantan Utara":     (2.50,    4.30, 115.00, 118.00),
    "Sulawesi Utara":       (0.35,    4.22, 123.23, 127.00),
    "Gorontalo":            (0.37,    0.93, 121.73, 123.42),
    "Sulawesi Tengah":      (-3.80,   1.72, 119.25, 124.70),
    "Sulawesi Selatan":     (-8.33,  -0.85, 118.73, 122.00),
    "Sulawesi Barat":       (-3.65,  -0.85, 118.73, 119.65),
    "Sulawesi Tenggara":    (-6.25,  -3.52, 120.00, 124.20),
    "Maluku":               (-8.82,  -2.52, 126.00, 132.80),
    "Maluku Utara":         (-2.00,   3.75, 124.00, 129.60),
    "Papua":                (-9.00,  -1.00, 131.00, 141.02),
    "Papua Barat":          (-4.50,  -0.25, 130.00, 135.00),
}

NATIONAL_AVG_CAGR = 0.0125

# =========================
# HELPER FUNCTIONS
# =========================

def get_province(lat, lon):
    """Deteksi provinsi dari koordinat via bounding box."""
    candidates = []
    for prov, (lat_min, lat_max, lon_min, lon_max) in PROVINCE_BOUNDS.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            candidates.append(prov)

    if not candidates:
        # Fallback: centroid terdekat
        min_dist = float('inf')
        nearest = "Jawa Barat"
        for prov, (lat_min, lat_max, lon_min, lon_max) in PROVINCE_BOUNDS.items():
            clat = (lat_min + lat_max) / 2
            clon = (lon_min + lon_max) / 2
            d = ((lat - clat) ** 2 + (lon - clon) ** 2) ** 0.5
            if d < min_dist:
                min_dist = d
                nearest = prov
        return nearest

    # Jika overlap bounding box, ambil yang areanya paling kecil (paling presisi)
    return min(candidates, key=lambda p: (
        (PROVINCE_BOUNDS[p][1] - PROVINCE_BOUNDS[p][0]) *
        (PROVINCE_BOUNDS[p][3] - PROVINCE_BOUNDS[p][2])
    ))


def get_cagr(province):
    """Ambil CAGR untuk provinsi. Fallback ke rata-rata nasional."""
    if province in PROVINCE_GROWTH:
        return PROVINCE_GROWTH[province][2]
    return NATIONAL_AVG_CAGR


# =========================
# REGION CLASSIFICATION
# =========================
def classify_region(lat, lon):
    if -6.5 < lat < -5.8 and 106.5 < lon < 107.2:
        return "jabodetabek"
    elif -8.0 < lat < -5.5 and 105.0 < lon < 114.0:
        return "jawa_non_jabodetabek"
    else:
        return "non_jawa"


def get_radius(region):
    return {"jabodetabek": 1000, "jawa_non_jabodetabek": 1500, "non_jawa": 2000}.get(region, 1000)


def classify_density(density):
    if density == 0:
        return "no_population"
    elif density <= 10000:
        return "low"
    elif density <= 14000:
        return "medium"
    elif density <= 18000:
        return "high"
    else:
        return "very_high"


# =========================
# MAIN FUNCTION
# =========================
def get_population_data(lat, lon):
    region   = classify_region(lat, lon)
    radius   = get_radius(region)
    province = get_province(lat, lon)
    cagr     = get_cagr(province)

    # Buffer dalam EPSG:3857 → konversi ke EPSG:4326 untuk masking raster
    x, y = to_3857.transform(lon, lat)
    buffer_3857 = Point(x, y).buffer(radius)
    geom = gpd.GeoSeries([buffer_3857], crs="EPSG:3857").to_crs("EPSG:4326").geometry.iloc[0]

    density_2020   = 0.0
    total_pop_2020 = 0.0

    try:
        if raster_bounds.intersects(geom):
            out_image, out_transform = mask(src, [geom], crop=True)
            data = out_image[0]

            # Resolusi pixel → luas pixel dalam km²
            pixel_width_deg  = abs(out_transform[0])
            pixel_height_deg = abs(out_transform[4])
            pixel_area_km2   = (
                (pixel_height_deg * 111.32) *
                (pixel_width_deg  * 111.32 * math.cos(math.radians(lat)))
            )

            nodata = src.nodata if src.nodata is not None else -99999.0
            valid  = (data != nodata) & (data >= 0)
            valid_pixels = data[valid]

            if len(valid_pixels) > 0:
                # ✅ Total populasi = Σ(density_pixel × luas_pixel)
                total_pop_2020 = float(np.sum(valid_pixels * pixel_area_km2))
                # ✅ Rata-rata density = mean semua pixel valid
                density_2020   = float(np.mean(valid_pixels))

    except Exception:
        density_2020   = 0.0
        total_pop_2020 = 0.0

    # =========================
    # PROYEKSI 2026 (6 tahun dari base year 2020)
    # Formula: P_t = P_2020 × (1 + CAGR)^n
    # =========================
    years          = 6
    growth_factor  = (1 + cagr) ** years
    total_pop_2026 = total_pop_2020 * growth_factor
    density_2026   = density_2020   * growth_factor

    return {
        "lat":    lat,
        "lon":    lon,
        "region": region,
        "radius_m": radius,
        "province": province,

        # Data 2020 — dipertahankan untuk kompatibilitas ML model
        "population_density_2020": round(density_2020,   2),
        "population_2020":         round(total_pop_2020),

        # Proyeksi 2026 — yang ditampilkan di UI
        "population_density_2026": round(density_2026,   2),
        "population_2026":         round(total_pop_2026),

        # Growth info
        "growth_rate":         round(cagr * 100, 3),
        "growth_rate_annual":  round(cagr * 100, 3),   # dipakai ML pipeline
        "growth_source":       f"BPS Sensus 2010 & 2020, Prov. {province}",

        # Kategori density 2026
        "category": classify_density(density_2026),
    }