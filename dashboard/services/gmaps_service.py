import requests
import math

# =========================
# 🔑 API KEY
# =========================
API_KEY = "AIzaSyBmPcCht7S9Y5p2ycWrqKiGLrEBoXUKyYY"


# =========================
# 📍 RADIUS RULE
# =========================
def get_radius(region):

    region = region.lower()

    if region == "jabodetabek":
        return 1000

    elif region in ["jawa", "jawa_non_jabodetabek"]:
        return 1500

    else:
        return 2000


# =========================
# 🔥 CALL GOOGLE PLACES API (POI VERSION FIXED)
# =========================
def get_places(lat, lng, place_type, radius):

    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location,places.types"
    }

    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(lat),
                    "longitude": float(lng)
                },
                "radius": radius
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    print(f"[DEBUG {place_type}] STATUS:", data)

    places = data.get("places", [])

    count = min(len(places), 20)
    capped = 1 if len(places) >= 20 else 0

    return {
        "count": count,
        "capped": capped
    }


# =========================
# 🏪 COMPETITOR FUNCTION (FIXED VERSION)
# =========================
def get_competitor_data(lat, lng, radius):

    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.types"
    }

    payload = {
        "includedTypes": [
            "supermarket",
            "convenience_store"
        ],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(lat),
                    "longitude": float(lng)
                },
                "radius": radius
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    print("\n[DEBUG COMPETITOR]")
    print(data)

    places = data.get("places", [])

    alfamidi = 0
    minimarket = 0
    supermarket = 0

    for p in places:

        name = p.get("displayName", {}).get("text", "").lower()
        types = p.get("types", [])

        if "supermarket" in types:
            supermarket += 1

        elif "convenience_store" in types:

            if "alfamidi" in name:
                alfamidi += 1
            else:
                minimarket += 1

    total = alfamidi + minimarket + supermarket

    # Kita hapus capped_total agar angka tidak tertahan di 10
    is_capped = 1 if total > 10 else 0

    area = math.pi * ((radius / 1000) ** 2)

    return {
        "alfamidi_count": alfamidi,
        "other_minimarket_count": minimarket,
        "supermarket_count": supermarket,
        "total_competitor": total,  # <--- Ganti jadi 'total'
        "density": round(total / area, 2),
        "is_capped": is_capped
    }


# =========================
# 🧠 MAIN FUNCTION
# =========================
def get_poi_competitor(lat, lng, region):

    radius = get_radius(region)

    # =========================
    # POI TYPES (FIXED VERSION)
    # =========================
    poi_types = [
        "restaurant",
        "school",
        "bank",
        "hospital"
    ]

    result = {
        "lat": float(lat),
        "lng": float(lng),
        "region": region,
        "radius": radius,
        "poi": {},
        "competitor": {},
        "summary": {}
    }

    total_poi = 0

    # =========================
    # 🍽️ POI PROCESS
    # =========================
    for t in poi_types:

        res = get_places(lat, lng, t, radius)

        result["poi"][t] = res
        total_poi += res["count"]

    # =========================
    # 🏪 COMPETITOR PROCESS
    # =========================
    competitor_res = get_competitor_data(lat, lng, radius)

    result["competitor"] = competitor_res

    total_competitor = competitor_res["total_competitor"]

    # =========================
    # 📊 SUMMARY
    # =========================
    result["summary"] = {
        "total_poi": total_poi,
        "total_competitor": total_competitor,
        "poi_status": "HIGH" if total_poi >= 20 else "NORMAL",
        "competitor_status": "HIGH" if total_competitor >= 10 else "LOW-MEDIUM"
    }

    return result


# =========================
# 🚀 TESTING
# =========================
if __name__ == "__main__":

    lat = -6.200000
    lng = 106.816666

    result = get_poi_competitor(
        lat,
        lng,
        region="jabodetabek"
    )

    print("\n=== FINAL RESULT ===")
    print(result)