import os
import joblib
import pandas as pd
import numpy as np
import re
import logging
import traceback
from django.conf import settings

logger = logging.getLogger(__name__)

# 1. SETUP PATH DIREKTORI DATA
BASE_DIR = settings.BASE_DIR
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 2. LOAD SEMUA ASSET (Jabodetabek & Non-Jabodetabek)
try:
    # Asset Jabodetabek
    model_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_model (2).pkl"))
    features_jabo = joblib.load(os.path.join(DATA_DIR, "feature_columns (1).pkl"))
    thresholds_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_thresholds (1).pkl"))

    # Asset Non-Jabodetabek
    model_non_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_model (3).pkl"))
    features_non_jabo = joblib.load(os.path.join(DATA_DIR, "feature_columns (2).pkl"))
    thresholds_non_jabo = joblib.load(os.path.join(DATA_DIR, "traffic_thresholds (2).pkl"))

    print("✅ Berhasil memuat seluruh model Jabodetabek & Non-Jabodetabek!")
except Exception as e:
    # NOTE: sebelumnya di sini cuma print(e) singkat sehingga penyebab asli
    # (mismatch versi sklearn/joblib, file korup, path salah, dll) tidak
    # pernah terlihat di console/log. Sekarang traceback lengkap dicetak
    # agar akar masalah bisa ditemukan langsung dari log server.
    print(f"❌ Gagal memuat asset model traffic (Jabodetabek/Non-Jabodetabek): {e}")
    traceback.print_exc()
    logger.error("Gagal memuat asset model traffic pipeline", exc_info=True)
    model_jabo = model_non_jabo = None
    features_jabo = features_non_jabo = None
    thresholds_jabo = thresholds_non_jabo = None

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
    wilayah = "Jabodetabek" if is_jabo else "Luar Jabodetabek"

    try:
        # ── Ambil road_types lebih dulu (dipakai untuk road_type_count & one-hot) ──
        road_types_input = feature_source_data.get("road_types", [])
        if not isinstance(road_types_input, list):
            road_types_input = [road_types_input]

        total_poi = int(feature_source_data.get("total_poi", 0))
        intersection_count = int(feature_source_data.get("intersection_count", 0))
        is_main_road = int(feature_source_data.get("is_main_road", 1))

        # 1. Blueprint mapping dari key views ke nama kolom PERSIS seperti
        # yang ada di feature_columns (1).pkl / (2).pkl.
        #
        # PENTING (perbaikan bug):
        # - "other_minimarket_count" & "supermarket_count" sebelumnya ditulis
        #   sebagai "minimarket_found" / "supermarket_found" -> nama itu TIDAK
        #   ADA di feature_columns pkl, jadi saat reindex() nilainya selalu
        #   ditimpa jadi 0 walau datanya sebenarnya ada.
        # - "school_count" sebelumnya tidak pernah di-mapping sama sekali
        #   -> selalu 0 padahal views.py sudah mengirim datanya.
        # - "poi_x_intersection", "poi_x_mainroad", "road_type_count" adalah
        #   fitur hasil rekayasa (feature engineering) saat training yang
        #   sebelumnya tidak pernah dihitung ulang di pipeline ini -> selalu 0.
        #   Padahal "poi_x_intersection" adalah fitur ke-2 paling penting di
        #   kedua model (>7% importance).
        # - "*_is_capped" adalah flag apakah count aslinya dipotong (capped)
        #   saat training. Importance-nya sangat kecil (<1%) dan kita tidak
        #   tahu persis ambang capping yang dipakai saat training, jadi di-set
        #   0 (asumsi tidak capped) agar aman -- tidak menambah bias baru.
        base_data = {
            "restaurant_count": int(feature_source_data.get("restaurant_count", 0)),
            "restaurant_is_capped": 0,
            "school_count": int(feature_source_data.get("school_count", 0)),
            "school_is_capped": 0,
            "bank_count": int(feature_source_data.get("bank_count", 0)),
            "bank_is_capped": 0,
            "hospital_count": int(feature_source_data.get("hospital_count", 0)),
            "hospital_is_capped": 0,
            "total_poi": total_poi,
            "is_main_road": is_main_road,
            "intersection_count": intersection_count,
            "other_minimarket_count": int(feature_source_data.get("other_minimarket_count", 0)),
            "supermarket_count": int(feature_source_data.get("supermarket_count", 0)),
            "road_type_count": len(set(road_types_input)),
            "poi_x_intersection": total_poi * intersection_count,
            "poi_x_mainroad": total_poi * is_main_road,
        }

        # Semua kemungkinan one-hot road_types dari kedua feature_columns pkl
        # digabung di sini; reindex() di bawah otomatis akan mengambil hanya
        # kolom yang benar-benar dipakai model_jabo / model_non_jabo masing-masing.
        semua_jenis_jalan = [
            "0", "living_street", "motorway", "motorway_link", "primary",
            "primary_link", "residential", "secondary", "secondary_link",
            "tertiary", "tertiary_link", "trunk", "trunk_link", "unclassified",
        ]
        for rt in semua_jenis_jalan:
            base_data[f"road_types_{rt}"] = int(rt in road_types_input)

        df = pd.DataFrame([base_data])

        if is_jabo:
            if model_jabo is None:
                raise RuntimeError("Model Jabodetabek tidak berhasil dimuat (cek log server saat startup).")

            # Sinkronisasi & Reorder Column agar pas dengan list features_jabo (.pkl)
            df_ready = df.reindex(columns=features_jabo, fill_value=0)

            # Predict
            score = model_jabo.predict(df_ready)[0]
            category, recommendation = proses_jabodetabek(score)

        else:
            if model_non_jabo is None:
                raise RuntimeError("Model Non-Jabodetabek tidak berhasil dimuat (cek log server saat startup).")

            # Sinkronisasi & Reorder Column agar pas dengan list features_non_jabo (.pkl)
            df_ready = df.reindex(columns=features_non_jabo, fill_value=0)

            # Predict
            score = model_non_jabo.predict(df_ready)[0]
            category, recommendation = proses_non_jabodetabek(score)

        return {
            "wilayah_terdeteksi": wilayah,
            "traffic_score": round(float(score), 2),
            "category": category,
            "recommendation": recommendation,
        }

    except Exception as e:
        # PENTING: sebelumnya kegagalan di sini (model None atau predict error)
        # membuat "wilayah_terdeteksi" ikut hilang, sehingga kolom Region di
        # tabel Riwayat & Traffic Estimation di PDF tampil "-" walau
        # sebenarnya wilayah (Jabodetabek/Luar Jabodetabek) sudah bisa
        # dipastikan hanya dari koordinat. Sekarang wilayah tetap dikirim
        # balik meski prediksi traffic gagal, dan errornya dicatat ke log.
        logger.error("Gagal menjalankan prediksi traffic pipeline", exc_info=True)
        print(f"⚠️ analyze_traffic_pipeline gagal memprediksi: {e}")
        return {
            "wilayah_terdeteksi": wilayah,
            "traffic_score": 0,
            "category": "Tidak diketahui",
            "recommendation": "-",
            "error": str(e),
        }