import os
import joblib
import pandas as pd
import numpy as np
import re
from django.conf import settings

# 1. SETUP PATH DIREKTORI DATA
BASE_DIR = settings.BASE_DIR
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 2. LOAD SEMUA ASSET (Jabodetabek & Non-Jabodetabek)
try:
    # Asset Jabodetabek
    model_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_model.pkl"))
    features_jabo = joblib.load(os.path.join(DATA_DIR, "feature_columns.pkl"))
    thresholds_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_thresholds.pkl"))
    
    # Asset Non-Jabodetabek
    model_non_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_model_non_jabodetabek (1).pkl"))
    features_non_jabo = joblib.load(os.path.join(DATA_DIR, "feature_columns_non_jabodetabek.pkl"))
    thresholds_non_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_threshold_non_jabodetabek.pkl"))
    
    print("✅ Berhasil memuat seluruh model Jabodetabek & Non-Jabodetabek!")
except Exception as e:
    print(f"❌ Gagal memuat asset model: {e}")
    model_jabo = model_non_jabo = None

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def cek_apakah_jabodetabek(lat, lon):
    if (-6.82 <= lat <= -5.91) and (106.32 <= lon <= 107.30):
        return True
    return False

def extract_num(text):
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(text))
    return float(nums[0]) if nums else 0.0

# =========================================================
# EVALUATION CHANNELS
# =========================================================

def proses_jabodetabek(prediction_score):
    low_limit = 110.41
    high_limit = 175.05
    
    if prediction_score < low_limit:
        return "Low", "Not Recommended"
    elif prediction_score <= high_limit:
        return "Medium", "Considered"
    else:
        return "High", "Highly Recommended"

def proses_non_jabodetabek(prediction_score):
    low_limit = extract_num(thresholds_non_jabo.get('Low', 5.098)) if thresholds_non_jabo else 5.098
    high_limit = extract_num(thresholds_non_jabo.get('High', 5.647)) if thresholds_non_jabo else 5.647
    
    if prediction_score >= high_limit:
        return "High", "Highly Recommended"
    elif prediction_score >= low_limit:
        return "Medium", "Considered"
    else:
        return "Low", "Not Recommended"

# =========================================================
# MAIN PIPELINE CORE
# =========================================================

def analyze_traffic_pipeline(lat, lon, feature_source_data):
    lat = float(lat)
    lon = float(lon)
    is_jabo = cek_apakah_jabodetabek(lat, lon)
    
    # 1. Blueprint mapping awal dari key views ke nama kolom murni
    # Menghindari miskonsepsi nama variabel
    base_data = {
        "total_poi": int(feature_source_data.get("total_poi", 0)),
        "intersection_count": int(feature_source_data.get("intersection_count", 0)),
        "minimarket_found": int(feature_source_data.get("other_minimarket_count", 0)),
        "supermarket_found": int(feature_source_data.get("supermarket_count", 0)),
        "hospital_count": int(feature_source_data.get("hospital_count", 0)),
        "is_main_road": int(feature_source_data.get("is_main_road", 1)),
        "bank_count": int(feature_source_data.get("bank_count", 0)),
        "restaurant_count": int(feature_source_data.get("restaurant_count", 0)),
    }
    
    df = pd.DataFrame([base_data])
    
    if is_jabo:
        if model_jabo is None: return {"error": "Model Jabodetabek tidak aktif"}
        
        # ─── PREPROCESSING SPESIFIK JABODETABEK ───
        # Berdasarkan grafik: butuh road_types_secondary, road_types_tertiary, road_types_residential
        road_types_input = feature_source_data.get("road_types", [])
        if not isinstance(road_types_input, list):
            road_types_input = [road_types_input]
            
        df["road_types_secondary"] = int("secondary" in road_types_input)
        df["road_types_tertiary"] = int("tertiary" in road_types_input)
        df["road_types_residential"] = int("residential" in road_types_input)
        
        # Sinkronisasi & Reorder Column agar pas dengan list features_jabo (.pkl)
        df_ready = df.reindex(columns=features_jabo, fill_value=0)
        
        # Predict
        score = model_jabo.predict(df_ready)[0]
        category, recommendation = proses_jabodetabek(score)
        wilayah = "Jabodetabek"
        
    else:
        if model_non_jabo is None: return {"error": "Model Non-Jabodetabek tidak aktif"}
        
        # ─── PREPROCESSING SPESIFIK NON-JABODETABEK ───
        # Berdasarkan grafik: butuh total_poi_scaled (total_poi / 100)
        df["total_poi_scaled"] = df["total_poi"] / 100.0
        
        # Tambahan one-hot encoding untuk jalan jika model non-jabo memintanya di list pkl
        road_types_input = feature_source_data.get("road_types", [])
        if not isinstance(road_types_input, list):
            road_types_input = [road_types_input]
            
        df["road_types_primary"] = int("primary" in road_types_input)
        df["road_types_secondary"] = int("secondary" in road_types_input)
        df["road_types_tertiary"] = int("tertiary" in road_types_input)
        df["road_types_residential"] = int("residential" in road_types_input)
        
        # Sinkronisasi & Reorder Column agar pas dengan list features_non_jabo (.pkl)
        df_ready = df.reindex(columns=features_non_jabo, fill_value=0)
        
        # Predict
        score = model_non_jabo.predict(df_ready)[0]
        category, recommendation = proses_non_jabodetabek(score)
        wilayah = "Luar Jabodetabek"

    return {
        "wilayah_terdeteksi": wilayah,
        "traffic_score": round(float(score), 2),
        "category": category,
        "recommendation": recommendation
    }