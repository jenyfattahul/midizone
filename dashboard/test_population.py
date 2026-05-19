from services.population_service import get_population_data

if __name__ == "__main__":

    lat = -6.143705
    lon = 106.869257

    result = get_population_data(lat, lon)

    print("\n=== POPULATION TEST ===")
    print(result)