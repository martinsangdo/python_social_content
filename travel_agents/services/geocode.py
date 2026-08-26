import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_city(city_name: str) -> dict:
    """Look up a city's coordinates via the free Open-Meteo Geocoding API.

    Returns {"name", "country", "latitude", "longitude"} or raises ValueError
    if the city cannot be found. No mock/fallback coordinates are ever returned.
    """
    resp = requests.get(
        GEOCODE_URL,
        params={"name": city_name, "count": 1, "language": "en", "format": "json"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Could not find coordinates for city '{city_name}'.")

    top = results[0]
    return {
        "name": top["name"],
        "country": top.get("country"),
        "latitude": top["latitude"],
        "longitude": top["longitude"],
    }
