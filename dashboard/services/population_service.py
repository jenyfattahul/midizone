import os
import math
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point
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

# =========================
# TRANSFORMER
# =========================
to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

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
    if region == "jabodetabek":
        return 1000
    elif region == "jawa_non_jabodetabek":
        return 1500
    else:
        return 2000

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
# GROWTH RATE MODEL (2020 → 2026)
# =========================
def get_growth_rate(density, region):
    if density == 0:
        return 0.0
    elif density <= 10000:
        rate = 0.017
    elif density <= 14000:
        rate = 0.013
    elif density <= 18000:
        rate = 0.009
    else:
        rate = 0.005

    if region == "non_jawa":
        rate += 0.002

    return rate

# =========================
# MAIN FUNCTION
# =========================
def get_population_data(lat, lon):
    region = classify_region(lat, lon)
    radius = get_radius(region)

    # convert latlon → meter
    x, y = to_3857.transform(lon, lat)
    point = Point(x, y)
    buffer = point.buffer(radius)

    geom = gpd.GeoSeries([buffer], crs="EPSG:3857").to_crs("EPSG:4326").geometry.iloc[0]

    density_2020 = 0

    try:
        if src.bounds[0] <= lon <= src.bounds[2] and src.bounds[1] <= lat <= src.bounds[3]:
            out_image, _ = mask(src, [geom], crop=True)
            data = out_image[0].flatten()

            if src.nodata is not None:
                data = data[data != src.nodata]

            density_2020 = np.median(data) if len(data) > 0 else 0

    except Exception:
        density_2020 = 0

    # =========================
    # AREA & POPULATION 2020
    # =========================
    area_km2 = math.pi * (radius / 1000) ** 2
    pop_2020 = density_2020 * area_km2

    # =========================
    # PROJECTION 2026
    # =========================
    years = 6
    growth_rate = get_growth_rate(density_2020, region)

    pop_2026 = pop_2020 * ((1 + growth_rate) ** years)
    density_2026 = density_2020 * ((1 + growth_rate) ** years)

    return {
    "lat": lat,
    "lon": lon,
    "region": region,
    "radius_m": radius,

    # =========================
    # 2020 BASE DATA
    # =========================
    "population_density_2020": round(float(density_2020), 2),
    "population_2020": round(float(pop_2020), 2),

    # =========================
    # 2026 PROJECTION (FINAL OUTPUT ML)
    # =========================
    "population_density_2026": round(float(density_2026), 2),
    "population_2026": round(float(pop_2026), 2),

    # =========================
    # EXTRA INFO
    # =========================
    "growth_rate": round(growth_rate * 100, 2),
    "category": classify_density(density_2026)
}