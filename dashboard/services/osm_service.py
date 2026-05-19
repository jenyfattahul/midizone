import osmnx as ox

# ======================================
# FUNCTION AMBIL GRAPH
# ======================================

def get_graph(lat, lon):

    for dist in [300, 400, 500]:

        try:

            G = ox.graph_from_point(
                (lat, lon),
                dist=dist,
                network_type='drive'
            )

            return G

        except:

            print(f"Retry radius {dist} gagal...")

    return None


# ======================================
# ROAD TYPES
# ======================================

def get_road_types(G):

    try:

        edges = ox.graph_to_gdfs(G, nodes=False)

        highways = edges['highway'].explode().unique()

        return list(highways)

    except:

        return []


# ======================================
# TRANSLATE ROAD TYPES
# ======================================

def translate_road_types(road_types):

    mapping = {

        "motorway": "jalan tol / highway",
        "motorway_link": "akses masuk/keluar tol",

        "trunk": "jalan besar penghubung antar kota",
        "trunk_link": "akses jalan besar",

        "primary": "jalan utama kota",
        "primary_link": "akses jalan utama",

        "secondary": "jalan penghubung utama",
        "secondary_link": "akses jalan penghubung",

        "tertiary": "jalan lokal besar",
        "tertiary_link": "akses jalan lokal",

        "residential": "jalan perumahan",
        "living_street": "jalan kecil / gang",

        "unclassified": "jalan umum kecil",
        "service": "jalan layanan / parkiran"
    }

    return [mapping.get(rt, rt) for rt in road_types]


# ======================================
# ROAD SCORE
# ======================================

def road_score(road_types):

    weights = {
        "motorway": 2,
        "trunk": 3,
        "primary": 5,
        "secondary": 4,
        "tertiary": 3,
        "residential": 2,
        "living_street": 1
    }

    score = 0

    for rt in road_types:

        score += weights.get(rt, 0)

    return min(score, 10)


# ======================================
# MAIN ROAD FLAG
# ======================================

def is_main_road(road_types):

    return int(
        any(
            rt in ["primary", "secondary", "trunk"]
            for rt in road_types
        )
    )


# ======================================
# INTERSECTION COUNT
# ======================================

def get_intersection_count(G):

    try:

        degrees = dict(G.degree())

        intersections = [
            node
            for node, deg in degrees.items()
            if deg >= 3
        ]

        return len(intersections)

    except:

        return 0


# ======================================
# MAIN FUNCTION
# ======================================

def process_road_features(lat, lon):

    G = get_graph(lat, lon)

    if G is None:

        return {
            "road_types": "",
            "road_types_desc": "",
            "road_score": 0,
            "is_main_road": 0,
            "intersection_count": 0
        }

    roads = get_road_types(G)

    translated = translate_road_types(roads)

    score = road_score(roads)

    main = is_main_road(roads)

    intersections = get_intersection_count(G)

    result = {

        "road_types": ",".join(map(str, roads)),

        "road_types_desc": ",".join(translated),

        "road_score": score,

        "is_main_road": main,

        "intersection_count": intersections
    }

    return result