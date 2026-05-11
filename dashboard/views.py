from django.shortcuts import render
import datetime
from django.contrib.auth.decorators import login_required


def login_view(request):
    return render(request, "login.html")


# Matikan dulu sementara dengan tanda #
# @login_required(login_url='login')
def dashboard_view(request):
    return render(request, "dashboard.html")


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


# Matikan dulu sementara dengan tanda #
# @login_required(login_url='login')
def input_lokasi(request):
    context = {
        "latitude": "-6.2081",
        "longitude": "106.8227",
        "provinsi": "Banten",
        "kota": "Tangerang",
        "nama_jalan": "Jalan Sutera Barat",
        "total_poi": 20,
        "total_kompetitor": 15,
        "estimasi_traffic": "Tinggi",
        "status_kelayakan": "LAYAK",
        "confidence_score": 87,
        "daftar_poi": [
            {"nama": "Indomaret", "jarak": 0.1},
            {"nama": "RS Umum", "jarak": 0.8},
            {"nama": "Alfamart", "jarak": 0.15},
        ],
    }
    return render(request, "input_lokasi.html", context)


# Matikan dulu sementara dengan tanda #
# @login_required(login_url='login')
def riwayat_view(request):
    context = {}
    return render(request, "riwayat.html", context)
