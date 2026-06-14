import json
import os
import datetime
import joblib
import pandas as pd
from geopy.geocoders import Nominatim
import h3
from weasyprint import HTML

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string

# Import services
from .services.gmaps_service import get_poi_competitor
from .services.osm_service import process_road_features
from .services.population_service import get_population_data
from .services.traffic_pipeline import analyze_traffic_pipeline
from .models import (
    AnalysisPopulation,
    AnalysisSnapshot,
    Location,
    ModelResult,
    SiteAnalysis,
)

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "data", "location_optimization_model.pkl")
)
SCALER_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "data", "spatial_scaler_model.pkl")
)


# Helper Functions
def get_indonesian_date():
    bulan = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "Mei",
        "Jun",
        "Jul",
        "Ags",
        "Sep",
        "Okt",
        "Nov",
        "Des",
    ]
    now = datetime.datetime.now()
    return f"{now.day:02d}-{bulan[now.month - 1]}-{now.year} {now.strftime('%H:%M:%S')} WIB"


def get_roman_month(month):
    roman_numerals = {
        1: "I",
        2: "II",
        3: "III",
        4: "IV",
        5: "V",
        6: "VI",
        7: "VII",
        8: "VIII",
        9: "IX",
        10: "X",
        11: "XI",
        12: "XII",
    }
    return roman_numerals.get(month, "I")


def clean_int(val):
    try:
        clean_str = "".join(filter(lambda x: x.isdigit() or x == ".", str(val)))
        return int(float(clean_str))
    except (ValueError, TypeError):
        return 0


def clean_float(val):
    try:
        return float(str(val).replace(",", ".").strip())
    except:
        return 0.0


from django.db.models import Avg
from .models import SiteAnalysis, ModelResult


@login_required(login_url="login")
def dashboard_view(request):

    total_analisis = SiteAnalysis.objects.count()

    total_layak = ModelResult.objects.filter(feasibility_prediction="LAYAK").count()

    total_tidak_layak = ModelResult.objects.filter(
        feasibility_prediction="TIDAK LAYAK"
    ).count()

    avg_confidence = (
        ModelResult.objects.aggregate(avg=Avg("confidence_score"))["avg"] or 0
    )

    top_locations = ModelResult.objects.select_related("analysis").order_by(
        "-confidence_score"
    )[:5]

    context = {
        "total_analisis": total_analisis,
        "total_layak": total_layak,
        "total_tidak_layak": total_tidak_layak,
        "avg_confidence": round(avg_confidence, 1),
        "top_locations": top_locations,
    }

    return render(
        request,
        "dashboard.html",
        context,
    )


@login_required(login_url="login")
def riwayat_view(request):
    riwayat_list = SiteAnalysis.objects.all().order_by("-input_date")
    context = {"riwayat_list": riwayat_list}
    return render(request, "riwayat.html", context)


@login_required(login_url="login")
def detail_riwayat(request, analysis_id):
    return detail_riwayat_partial(request, analysis_id)


@login_required(login_url="login")
def detail_riwayat_partial(request, analysis_id):
    analysis = SiteAnalysis.objects.get(analysis_id=analysis_id)
    snapshot = AnalysisSnapshot.objects.filter(analysis=analysis).first()
    demography = AnalysisPopulation.objects.filter(analysis=analysis).first()
    model = ModelResult.objects.filter(analysis=analysis).first()

    context = {
        "analysis": analysis,
        "snapshot": snapshot,
        "demography": demography,
        "model": model,
        "poi_data": {
            "restaurant": {"count": snapshot.restaurant_count if snapshot else 0},
            "school": {"count": snapshot.school_count if snapshot else 0},
            "bank": {"count": snapshot.bank_count if snapshot else 0},
            "hospital": {"count": snapshot.hospital_count if snapshot else 0},
        },
        "summary_data": {"total_poi": snapshot.total_poi if snapshot else 0},
        "competitor_data": {
            "supermarket_count": snapshot.supermarket_count if snapshot else 0,
            "other_minimarket_count": snapshot.other_minimarket_count
            if snapshot
            else 0,
            "alfamidi_count": snapshot.alfamidi_count if snapshot else 0,
            "total_competitor": snapshot.total_competitor if snapshot else 0,
        },
        "status_kelayakan": model.feasibility_prediction if model else "LAYAK",
        "confidence_score": model.confidence_score if model else 87,
        "category_ml": model.traffic_category_prediction if model else "Medium",
        "latitude": analysis.location.latitude,
        "longitude": analysis.location.longitude,
        "nama_jalan": analysis.location.address,
        "provinsi_kota": analysis.region,
        "road_types_desc": analysis.road_type,
        "intersection_count": analysis.intersection_count,
        "catatan_manager": "Detail data riwayat tersimpan.",
    }
    return render(request, "detail_content.html", context)


@login_required(login_url="login")
def input_lokasi(request):
    source = request.GET.get("source", "manual")
    koordinat = request.GET.get("koordinat", "")
    context = {
        "source": source,
        "koordinat": koordinat,
        "poi_data": {},
        "competitor_data": {},
        "summary_data": {},
        "latitude": "-",
        "longitude": "-",
        "nama_jalan": "-",
        "provinsi_kota": "-, -",
        "catatan_manager": "-",
        "road_types": None,
        "road_types_desc": "-",
        "intersection_count": 0,
        "status_kelayakan": "LAYAK",
        "confidence_score": 87,
        "h3_polygon_json": "[]",
        "poi_markers_json": "[]",
    }

    if koordinat:
        try:
            lat_str, lon_str = koordinat.split(",")
            lat, lon = float(lat_str.strip()), float(lon_str.strip())
            geolocator = Nominatim(user_agent="midizone_app")
            location = geolocator.reverse(f"{lat}, {lon}", timeout=10)

            nama_jalan, provinsi_kota, provinsi = "-", "-", "lainnya"
            if location:
                address = location.raw.get("address", {})
                nama_jalan = (
                    address.get("road")
                    or address.get("pedestrian")
                    or address.get("footway")
                    or address.get("residential")
                    or address.get("neighbourhood")
                    or address.get("suburb")
                    or address.get("village")
                    or "Nama jalan tidak terdeteksi"
                )
                kota = (
                    address.get("city")
                    or address.get("town")
                    or address.get("county")
                    or address.get("municipality")
                    or "-"
                )
                province_code = address.get("ISO3166-2-lvl4", "")
                province_mapping = {
                    "ID-AC": "Aceh",
                    "ID-SU": "Sumatera Utara",
                    "ID-SB": "Sumatera Barat",
                    "ID-RI": "Riau",
                    "ID-KR": "Kepulauan Riau",
                    "ID-JA": "Jambi",
                    "ID-SS": "Sumatera Selatan",
                    "ID-BB": "Bangka Belitung",
                    "ID-BE": "Bengkulu",
                    "ID-LA": "Lampung",
                    "ID-JK": "DKI Jakarta",
                    "ID-BT": "Banten",
                    "ID-JB": "Jawa Barat",
                    "ID-JT": "Jawa Tengah",
                    "ID-YO": "DI Yogyakarta",
                    "ID-JI": "Jawa Timur",
                    "ID-BA": "Bali",
                    "ID-NB": "Nusa Tenggara Barat",
                    "ID-NT": "Nusa Tenggara Timur",
                    "ID-KB": "Kalimantan Barat",
                    "ID-KT": "Kalimantan Tengah",
                    "ID-KS": "Kalimantan Selatan",
                    "ID-KI": "Kalimantan Timur",
                    "ID-KU": "Kalimantan Utara",
                    "ID-SA": "Sulawesi Utara",
                    "ID-ST": "Sulawesi Tengah",
                    "ID-SN": "Sulawesi Selatan",
                    "ID-SG": "Sulawesi Tenggara",
                    "ID-GO": "Gorontalo",
                    "ID-SR": "Sulawesi Barat",
                    "ID-MA": "Maluku",
                    "ID-MU": "Maluku Utara",
                    "ID-PA": "Papua",
                    "ID-PB": "Papua Barat",
                    "ID-PS": "Papua Selatan",
                    "ID-PT": "Papua Tengah",
                    "ID-PE": "Papua Pegunungan",
                    "ID-PD": "Papua Barat Daya",
                }
                provinsi = province_mapping.get(
                    province_code,
                    address.get("state")
                    or address.get("region")
                    or address.get("province")
                    or "-",
                )
                if "Jakarta" in location.raw.get("display_name", ""):
                    provinsi = "DKI Jakarta"
                provinsi_kota = f"{kota}, {provinsi}"

            road_data = process_road_features(lat, lon) or {}
            pop_data = get_population_data(lat, lon) or {}
            prov_kota_lower = provinsi_kota.lower()
            region = (
                "jabodetabek"
                if "jakarta" in prov_kota_lower
                else ("jawa" if "jawa" in prov_kota_lower else "lainnya")
            )
            poi_competitor_data = get_poi_competitor(lat, lon, region) or {}
            summary = poi_competitor_data.get("summary", {}) or {}
            road_types_list = road_data.get("road_types", [])
            is_main_road = (
                1
                if any(
                    rt in ["primary", "secondary", "tertiary"] for rt in road_types_list
                )
                else 0
            )

            scraped_features = {
                "restaurant_count": summary.get("Restaurant", 0),
                "school_count": summary.get("Sekolah", 0),
                "bank_count": summary.get("Bank/ATM", 0),
                "hospital_count": summary.get("RS/Hospital", 0),
                "supermarket_count": summary.get("Supermarket", 0),
                "other_minimarket_count": summary.get("Minimarket", 0),
                "total_poi": poi_competitor_data.get(
                    "total_poi", summary.get("Total POI", 0)
                ),
                "intersection_count": road_data.get("intersection_count", 0),
                "is_main_road": is_main_road,
                "road_types": road_types_list,
            }
            ml_results = (
                analyze_traffic_pipeline(
                    lat=lat, lon=lon, feature_source_data=scraped_features
                )
                or {}
            )
            h3_idx = (
                h3.latlng_to_cell(lat, lon, 9)
                if hasattr(h3, "latlng_to_cell")
                else h3.geo_to_h3(lat, lon, 9)
            )
            h3_boundaries = (
                h3.cell_to_boundary(h3_idx)
                if hasattr(h3, "cell_to_boundary")
                else h3.h3_to_geo_boundary(h3_idx)
            )
            h3_polygon_matrix = [[float(b[0]), float(b[1])] for b in h3_boundaries]

            markers_list = []
            raw_poi = poi_competitor_data.get("poi", {})
            raw_comp = poi_competitor_data.get("competitor", {})

            for poi_key in ["restaurant", "school", "bank", "hospital"]:
                items = (
                    raw_poi.get(poi_key, {}).get("items", [])
                    if isinstance(raw_poi.get(poi_key), dict)
                    else []
                )
                for item in items:
                    if "lat" in item and "lng" in item:
                        markers_list.append(
                            {
                                "name": item.get("name", poi_key),
                                "lat": float(item["lat"]),
                                "lng": float(item["lng"]),
                                "type": poi_key,
                            }
                        )

            for comp_key in [
                "supermarket_list",
                "other_minimarket_list",
                "alfamidi_list",
            ]:
                items = raw_comp.get(comp_key, []) if isinstance(raw_comp, dict) else []
                marker_type = "alfamidi" if "alfamidi" in comp_key else "competitor"
                for item in items:
                    if "lat" in item and "lng" in item:
                        markers_list.append(
                            {
                                "name": item.get("name", "Gerai Ritel"),
                                "lat": float(item["lat"]),
                                "lng": float(item["lng"]),
                                "type": marker_type,
                            }
                        )

            try:
                input_fitur_kontinu = [
                    float(summary.get("Restaurant", 0)),
                    float(summary.get("Sekolah", 0)),
                    float(summary.get("Bank/ATM", 0)),
                    float(summary.get("RS/Hospital", 0)),
                    float(raw_comp.get("alfamidi_count", 0)),
                    float(raw_comp.get("other_minimarket_count", 0)),
                    float(raw_comp.get("supermarket_count", 0)),
                    float(road_data.get("road_score", 0.0)),
                    float(road_data.get("intersection_count", 0)),
                    float(
                        str(pop_data.get("growth_rate_annual", 0.0))
                        .replace("%", "")
                        .strip()
                    )
                    / 100
                    if "%" in str(pop_data.get("growth_rate_annual", 0))
                    else float(pop_data.get("growth_rate_annual", 0.0)),
                    float(pop_data.get("population_2026", 0)),
                    float(
                        str(pop_data.get("population_density_2020", 0.0))
                        .replace(",", ".")
                        .strip()
                    ),
                    float(len(road_types_list)),
                    2.0,
                ]
                input_fitur_biner = [float(is_main_road)]
                model_kelayakan = joblib.load(MODEL_PATH)
                scaler_spasial = joblib.load(SCALER_PATH)
                nama_kolom_kontinu = [
                    "restaurant_count",
                    "school_count",
                    "bank_count",
                    "hospital_count",
                    "alfamidi_count",
                    "other_minimarket_count",
                    "supermarket_count",
                    "road_score",
                    "intersection_count",
                    "growth_rate_annual",
                    "pop_2026_est",
                    "density_2026_est",
                    "road_type_count",
                    "category_2026_encoded",
                ]
                df_input_kontinu = pd.DataFrame(
                    [input_fitur_kontinu], columns=nama_kolom_kontinu
                )
                fitur_kontinu_scaled = scaler_spasial.transform(df_input_kontinu)[0]
                nama_kolom_final = nama_kolom_kontinu + ["is_main_road"]
                fitur_final_gabungan = list(fitur_kontinu_scaled) + input_fitur_biner
                df_matrix_final = pd.DataFrame(
                    [fitur_final_gabungan], columns=nama_kolom_final
                )
                prediksi_kelas = model_kelayakan.predict(df_matrix_final)[0]
                probabilitas = model_kelayakan.predict_proba(df_matrix_final)[0]
                status_kelayakan = "LAYAK" if prediksi_kelas == 1 else "TIDAK LAYAK"
                confidence_score = int(probabilitas[prediksi_kelas] * 100)

                rest, sekolah, bank, rs = (
                    float(summary.get("Restaurant", 0)),
                    float(summary.get("Sekolah", 0)),
                    float(summary.get("Bank/ATM", 0)),
                    float(summary.get("RS/Hospital", 0)),
                )
                total_poi_social = rest + sekolah + bank + rs
                total_kompetitor_retail = (
                    float(raw_comp.get("alfamidi_count", 0))
                    + float(raw_comp.get("other_minimarket_count", 0))
                    + float(raw_comp.get("supermarket_count", 0))
                )
                pop_val = pop_data.get("population_2020")
                is_empty_pop = pop_val is None or pop_val == "-" or pop_val == 0

                if total_poi_social == 0 and is_empty_pop:
                    catatan_manager = "Catatan: Lokasi terdeteksi sebagai wilayah non-residensial (area perairan laut atau lahan kosong hampa). Karena parameter Populasi dan POI Sosial bernilai nol, investasi pembukaan gerai sangat dilarang."
                elif status_kelayakan == "LAYAK":
                    if confidence_score < 70:
                        catatan_manager = f"Catatan: Lokasi dinyatakan LAYAK karena daya tarik pasar yang kuat. Namun, tingkat kepercayaan {confidence_score}% dipengaruhi oleh persaingan {int(total_kompetitor_retail)} kompetitor ritel di radius tangkapan."
                    else:
                        catatan_manager = "Catatan: Lokasi dinilai sangat strategis berpotensi tinggi (Blue Ocean). Volume populasi ideal dengan tingkat kejenuhan kompetitor retail yang minim. Direkomendasikan untuk pengadaan lahan prioritas."
                else:
                    catatan_manager = f"Catatan: Lokasi TIDAK LAYAK. Tingkat kanibalisme pasar terlalu masif akibat kepungan {int(total_kompetitor_retail)} gerai ritel sejenis. ROI diprediksi lambat karena kue pangsa pasar sudah terbagi habis."
            except Exception as ml_error:
                print(f"⚠️ Gagal memproses model pkl Jeny: {ml_error}")
                status_kelayakan = ml_results.get("status_kelayakan", "LAYAK")
                confidence_score = (
                    int(ml_results.get("traffic_score", 87))
                    if ml_results.get("traffic_score")
                    else 87
                )
                catatan_manager = "Menggunakan fallback analitik karena kegagalan pemuatan model machine learning."

            context.update(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "nama_jalan": nama_jalan,
                    "provinsi_kota": provinsi_kota,
                    "road_types": road_types_list if road_types_list else ["local"],
                    "road_types_desc": road_data.get("road_types_desc", "-"),
                    "intersection_count": road_data.get("intersection_count", 0),
                    "population_density_2020": pop_data.get(
                        "population_density_2020", "-"
                    ),
                    "population_2020": pop_data.get("population_2020"),
                    "population_2026": pop_data.get("population_2026"),
                    "population_category": pop_data.get("category"),
                    "poi_data": raw_poi,
                    "competitor_data": raw_comp,
                    "summary_data": summary,
                    "radius": poi_competitor_data.get("radius", 0),
                    "wilayah_ml": ml_results.get("wilayah_terdeteksi", "-"),
                    "traffic_score": ml_results.get("traffic_score", 0),
                    "category_ml": ml_results.get("category", "-"),
                    "recommendation_ml": ml_results.get("recommendation", "-"),
                    "status_kelayakan": status_kelayakan,
                    "confidence_score": confidence_score,
                    "h3_polygon_json": json.dumps(h3_polygon_matrix),
                    "poi_markers_json": json.dumps(markers_list),
                    "catatan_manager": catatan_manager,
                }
            )
        except Exception as e:
            print(f"ERROR DI VIEWS INTEGRASI FINAL: {e}")
    return render(request, "input_lokasi.html", context)


@csrf_exempt
@login_required(login_url="login")
def hapus_riwayat(request, analysis_id):
    if request.method == "POST":
        try:
            analysis = SiteAnalysis.objects.get(analysis_id=analysis_id)
            analysis.delete()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error"}, status=405)


@login_required(login_url="login")
def simpan_lokasi(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Hanya metode POST"}, status=405
        )
    try:
        data = json.loads(request.body)
        user_default = User.objects.first() or User.objects.create_user(
            username="admin_midi", password="123"
        )
        lat = float(data.get("latitude", 0))
        lon = float(data.get("longitude", 0))
        alamat = data.get("address", "Nama jalan tidak terdeteksi")
        loc_obj = Location.objects.create(
            user=user_default, latitude=lat, longitude=lon, address=alamat
        )
        tanggal = datetime.datetime.now().strftime("%Y%m%d")
        analysis_obj = SiteAnalysis.objects.create(
            location=loc_obj,
            road_type=data.get("road_types_desc", "-"),
            intersection_count=int(data.get("intersection_count", 0)),
            region=data.get("region", "lainnya"),
            nomor_dokumen="PENDING",
        )
        analysis_obj.nomor_dokumen = (
            f"LOCSPEC/ANL/{tanggal}/{analysis_obj.analysis_id:03d}"
        )
        analysis_obj.save()
        AnalysisPopulation.objects.create(
            analysis=analysis_obj,
            population_density=clean_float(data.get("population_density_2020", 0)),
            population_2020=clean_int(data.get("population_2020", 0)),
            population_2026=clean_int(data.get("population_2026", 0)),
            population_category=data.get("population_category", "-"),
        )
        AnalysisSnapshot.objects.create(
            analysis=analysis_obj,
            restaurant_count=clean_int(data.get("restaurant_count", 0)),
            school_count=clean_int(data.get("school_count", 0)),
            bank_count=clean_int(data.get("bank_count", 0)),
            hospital_count=clean_int(data.get("hospital_count", 0)),
            total_poi=clean_int(data.get("total_poi", 0)),
            supermarket_count=clean_int(data.get("supermarket_count", 0)),
            other_minimarket_count=clean_int(data.get("other_minimarket_count", 0)),
            alfamidi_count=clean_int(data.get("alfamidi_count", 0)),
            total_competitor=clean_int(data.get("total_competitor", 0)),
        )
        ModelResult.objects.create(
            analysis=analysis_obj,
            feasibility_prediction=data.get("status_kelayakan", "LAYAK"),
            confidence_score=float(data.get("confidence_score", 87.0)),
            traffic_score_prediction=float(data.get("traffic_score", 0.0)),
            traffic_category_prediction=data.get("category_ml", "Medium"),
            pdf_link=f"LOCSPEC_ANL_V_2026_{analysis_obj.analysis_id}.pdf",
        )
        return JsonResponse(
            {
                "status": "success",
                "message": "Data berhasil disimpan!",
                "analysis_id": analysis_obj.analysis_id,
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required(login_url="login")
def road_feature_api(request):
    lat, lon = float(request.GET.get("lat", 0)), float(request.GET.get("lon", 0))
    result = process_road_features(lat, lon)
    return JsonResponse(result, safe=False)


@login_required(login_url="login")
def generate_pdf(request, analysis_id):
    analysis = SiteAnalysis.objects.get(analysis_id=analysis_id)
    snapshot = AnalysisSnapshot.objects.filter(analysis=analysis).first()
    demography = AnalysisPopulation.objects.filter(analysis=analysis).first()
    model = ModelResult.objects.filter(analysis=analysis).first()

    list_poi = [
        {"kategori": "Restaurant", "nama": f"{snapshot.restaurant_count or 0} unit"},
        {"kategori": "Sekolah", "nama": f"{snapshot.school_count or 0} unit"},
        {"kategori": "Bank/ATM", "nama": f"{snapshot.bank_count or 0} unit"},
        {"kategori": "Rumah Sakit", "nama": f"{snapshot.hospital_count or 0} unit"},
    ]
    list_kompetitor = [
        {"kategori": "Supermarket", "nama": f"{snapshot.supermarket_count or 0} unit"},
        {
            "kategori": "Minimarket Kompetitor",
            "nama": f"{snapshot.other_minimarket_count or 0} unit",
        },
        {
            "kategori": "Internal (Alfamidi)",
            "nama": f"{snapshot.alfamidi_count or 0} unit",
        },
    ]
    context = {
        "analysis": analysis,
        "snapshot": snapshot,
        "demography": demography,
        "model": model,
        "list_poi": list_poi,
        "list_kompetitor": list_kompetitor,
        "waktu_cetak": get_indonesian_date(),
    }

    html_string = render_to_string("template_pdf.html", context)
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Laporan_{analysis.nomor_dokumen.replace("/", "_")}.pdf"'
    )
    return response


import zipfile
import io
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML


def download_pdf_bulk(request):
    ids = request.GET.get("ids", "").split(",")
    if not ids or ids == [""]:
        return HttpResponse("Tidak ada data dipilih", status=400)

    # 1. Jika cuma satu ID, download PDF langsung
    if len(ids) == 1:
        return generate_pdf(request, ids[0])

    # 2. Jika banyak ID, buat ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for aid in ids:
            try:
                # Ambil data spesifik untuk ID ini
                analysis = SiteAnalysis.objects.get(analysis_id=aid)
                # Gunakan .first() untuk menghindari error jika data tidak ditemukan
                snapshot = AnalysisSnapshot.objects.filter(analysis=analysis).first()
                demography = AnalysisPopulation.objects.filter(
                    analysis=analysis
                ).first()
                model = ModelResult.objects.filter(analysis=analysis).first()

                # Jika snapshot tidak ada, buat objek kosong agar tidak error saat diakses
                # Kita pakai 0 sebagai fallback agar tidak merusak perhitungan
                list_poi = [
                    {
                        "kategori": "Restaurant",
                        "nama": f"{snapshot.restaurant_count if snapshot else 0} unit",
                    },
                    {
                        "kategori": "Sekolah",
                        "nama": f"{snapshot.school_count if snapshot else 0} unit",
                    },
                    {
                        "kategori": "Bank/ATM",
                        "nama": f"{snapshot.bank_count if snapshot else 0} unit",
                    },
                    {
                        "kategori": "Rumah Sakit",
                        "nama": f"{snapshot.hospital_count if snapshot else 0} unit",
                    },
                ]
                list_kompetitor = [
                    {
                        "kategori": "Supermarket",
                        "nama": f"{snapshot.supermarket_count if snapshot else 0} unit",
                    },
                    {
                        "kategori": "Minimarket Kompetitor",
                        "nama": f"{snapshot.other_minimarket_count if snapshot else 0} unit",
                    },
                    {
                        "kategori": "Internal (Alfamidi)",
                        "nama": f"{snapshot.alfamidi_count if snapshot else 0} unit",
                    },
                ]

                context = {
                    "analysis": analysis,
                    "snapshot": snapshot,
                    "demography": demography,
                    "model": model,
                    "list_poi": list_poi,
                    "list_kompetitor": list_kompetitor,
                    "waktu_cetak": get_indonesian_date(),
                }

                # Render template
                html_string = render_to_string("template_pdf.html", context)
                pdf_data = HTML(string=html_string).write_pdf()

                # Simpan ke ZIP dengan nama unik
                zf.writestr(
                    f"Laporan_{analysis.nomor_dokumen.replace('/', '_')}.pdf", pdf_data
                )
            except Exception as e:
                print(f"Error pada ID {aid}: {e}")
                continue

    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="Laporan_Analisis.zip"'
    return response


@csrf_exempt
@login_required(login_url="login")
def hapus_riwayat_batch(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])
            SiteAnalysis.objects.filter(analysis_id__in=ids).delete()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error"}, status=405)


@login_required(login_url="login")
def preview_pdf(request, analysis_id):
    analysis = SiteAnalysis.objects.get(analysis_id=analysis_id)
    snapshot = AnalysisSnapshot.objects.filter(analysis=analysis).first()
    demography = AnalysisPopulation.objects.filter(analysis=analysis).first()
    model = ModelResult.objects.filter(analysis=analysis).first()

    # --- TAMBAHKAN DATA INI SUPAYA DATA POI/KOMPETITOR MUNCUL ---
    list_poi = [
        {"kategori": "Restaurant", "nama": f"{snapshot.restaurant_count or 0} unit"},
        {"kategori": "Sekolah", "nama": f"{snapshot.school_count or 0} unit"},
        {"kategori": "Bank/ATM", "nama": f"{snapshot.bank_count or 0} unit"},
        {"kategori": "Rumah Sakit", "nama": f"{snapshot.hospital_count or 0} unit"},
    ]
    list_kompetitor = [
        {"kategori": "Supermarket", "nama": f"{snapshot.supermarket_count or 0} unit"},
        {
            "kategori": "Minimarket Kompetitor",
            "nama": f"{snapshot.other_minimarket_count or 0} unit",
        },
        {
            "kategori": "Internal (Alfamidi)",
            "nama": f"{snapshot.alfamidi_count or 0} unit",
        },
    ]
    # -----------------------------------------------------------

    context = {
        "analysis": analysis,
        "snapshot": snapshot,
        "demography": demography,
        "model": model,
        "list_poi": list_poi,  # PASTIKAN ADA
        "list_kompetitor": list_kompetitor,  # PASTIKAN ADA
        "waktu_cetak": get_indonesian_date(),
    }

    html_string = render_to_string("template_pdf.html", context)

    pdf = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    # inline = tampilkan di browser (preview)
    response["Content-Disposition"] = 'inline; filename="Preview.pdf"'
    # nosniff mencegah browser melakukan sniffing tipe konten
    response["X-Content-Type-Options"] = "nosniff"
    return response
