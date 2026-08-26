import os

import requests

AUTOCOMPLETE_URL = "https://autocomplete.travelpayouts.com/places2"
PRICES_FOR_DATES_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def _get_token() -> str:
    token = os.environ.get("TRAVELPAYOUTS_TOKEN")
    if not token:
        raise RuntimeError(
            "TRAVELPAYOUTS_TOKEN is not set. Add TRAVELPAYOUTS_TOKEN=<your token> to .env "
            "(free instant token after signing up at https://www.travelpayouts.com)."
        )
    return token


def resolve_place(name: str) -> dict:
    """Resolve a free-text place name to an IATA code + coordinates via the
    free, keyless Travelpayouts/Aviasales autocomplete API.

    Returns {"iataCode", "name", "type", "country", "latitude", "longitude"}.
    Raises ValueError if nothing is found. Never fabricates a code.
    """
    resp = requests.get(
        AUTOCOMPLETE_URL,
        params={"term": name, "locale": "en", "types[]": ["city", "airport"]},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json() or []
    if not results:
        raise ValueError(f"Could not resolve an IATA code for '{name}'.")

    # The API already returns results in relevance order for the search term;
    # `weight` is just global popularity and picking the highest-weight
    # result regardless of order can match an unrelated but busier place
    # (e.g. "Hanoi" -> Bucharest airport, which has a higher weight than
    # Hanoi itself). Prefer an exact case-insensitive name match, otherwise
    # trust the API's own ordering and take the first result.
    exact = next((r for r in results if r.get("name", "").lower() == name.strip().lower()), None)
    best = exact or results[0]
    coords = best.get("coordinates") or {}
    return {
        "iataCode": best["code"],
        "name": best.get("name", name),
        "type": best.get("type"),
        "country": best.get("country_name"),
        "latitude": coords.get("lat"),
        "longitude": coords.get("lon"),
    }


def search_one_way_prices(origin_iata: str, destination_iata: str, date: str,
                           limit: int = 10) -> list[dict]:
    """Search real cached one-way flight prices via the Aviasales v3 Data API.

    `date` accepts "YYYY-MM-DD" (a specific day) or "YYYY-MM" (a whole month).
    These are prices Aviasales users actually found in the last 48h for the
    route/date(s) -- not a live GDS booking search, and combined round-trip
    queries (single call with both a departure and return date) turn out to
    have very sparse cache coverage, so each leg is searched one-way and
    combined by the caller instead. Raises on API failure instead of
    returning fabricated data.
    """
    token = _get_token()
    params = {
        "origin": origin_iata,
        "destination": destination_iata,
        "departure_at": date,
        "currency": "usd",
        "sorting": "price",
        "direct": "false",
        "limit": limit,
        "page": 1,
        "one_way": "true",
        "token": token,
    }

    resp = requests.get(PRICES_FOR_DATES_URL, params=params, timeout=20)
    if not resp.ok:
        raise RuntimeError(f"Travelpayouts flight API error {resp.status_code}: {resp.text}")

    payload = resp.json()
    if not payload.get("success", True):
        raise RuntimeError(f"Travelpayouts flight API error: {payload.get('error')}")

    return payload.get("data") or []
