import math

import requests

from services.overpass_client import run_query

TOURISM_TAGS = "attraction|museum|viewpoint|gallery|artwork|zoo|theme_park|aquarium"
HISTORIC_TAGS = "monument|castle|memorial|ruins|archaeological_site"
WIKI_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
# Wikimedia requires a descriptive User-Agent on API requests (rejects the
# default python-requests UA with 403), per their robot policy.
WIKI_HEADERS = {"User-Agent": "travel-agents-planner/1.0 (Streamlit multi-agent trip planner)"}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _fetch_wikipedia_summary(wikipedia_tag: str | None) -> str | None:
    if not wikipedia_tag or ":" not in wikipedia_tag:
        return None
    lang, title = wikipedia_tag.split(":", 1)
    try:
        resp = requests.get(
            WIKI_SUMMARY_URL.format(lang=lang, title=title.replace(" ", "_")),
            headers=WIKI_HEADERS,
            timeout=10,
        )
    except requests.RequestException:
        return None
    if not resp.ok:
        return None
    return resp.json().get("extract")


def search_activities(latitude: float, longitude: float, radius_m: int = 6000,
                       limit: int = 8) -> list[dict]:
    """Search real points of interest via the free, keyless OpenStreetMap
    Overpass API (no registration required).

    Returns a list of {"name", "kinds", "distance_m", "description"} sorted
    by distance. Raises on API failure instead of returning fabricated data.
    """
    query = (
        f'[out:json][timeout:20];'
        f'(node["tourism"~"{TOURISM_TAGS}"](around:{radius_m},{latitude},{longitude});'
        f'node["historic"~"{HISTORIC_TAGS}"](around:{radius_m},{latitude},{longitude}););'
        f'out body {limit * 5};'
    )
    elements = run_query(query)

    seen_names = set()
    activities = []
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        activities.append({
            "name": name,
            "kinds": tags.get("tourism") or tags.get("historic"),
            "distance_m": round(_haversine_m(latitude, longitude, el["lat"], el["lon"])),
            "description": _fetch_wikipedia_summary(tags.get("wikipedia")),
        })

    activities.sort(key=lambda a: a["distance_m"])
    return activities[:limit]
