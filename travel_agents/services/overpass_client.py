import requests

# Public, keyless Overpass (OpenStreetMap) mirrors. Tried in order; the first
# one that answers wins. No registration/API key exists for this service.
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

# Overpass instances reject the default python-requests User-Agent (406);
# a descriptive UA is also good practice for a free, shared public service.
HEADERS = {"User-Agent": "travel-agents-planner/1.0 (Streamlit multi-agent trip planner)"}


def run_query(query: str, timeout: int = 25) -> list[dict]:
    """Run an Overpass QL query against the first mirror that responds.

    Returns the raw "elements" list. Raises RuntimeError only if every
    mirror fails -- never returns fabricated data.
    """
    errors = []
    for url in MIRRORS:
        try:
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=timeout)
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")
            continue

        if not resp.ok:
            errors.append(f"{url}: HTTP {resp.status_code}")
            continue

        try:
            return resp.json().get("elements") or []
        except ValueError:
            errors.append(f"{url}: invalid JSON response")

    raise RuntimeError(
        "All Overpass (OpenStreetMap) mirrors failed: " + "; ".join(errors)
    )
