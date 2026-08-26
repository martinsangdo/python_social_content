import os

import requests

HOST = "booking-com15.p.rapidapi.com"
BASE_URL = f"https://{HOST}/api/v1/hotels"


def _headers() -> dict:
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        raise RuntimeError(
            "RAPIDAPI_KEY is not set. Add RAPIDAPI_KEY=<your key> to .env -- "
            "create a free RapidAPI account at https://rapidapi.com, then subscribe to the "
            "free tier of the 'Booking.com' (DataCrawler) API at "
            "https://rapidapi.com/DataCrawler/api/booking-com15."
        )
    return {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": HOST}


def resolve_destination(query: str) -> dict:
    """Resolve a free-text place name to a Booking.com dest_id/search_type.

    Returns {"dest_id", "search_type", "name"}. Raises ValueError if nothing
    is found. Never fabricates an id.
    """
    resp = requests.get(
        f"{BASE_URL}/searchDestination",
        headers=_headers(),
        params={"query": query},
        timeout=20,
    )
    if not resp.ok:
        raise RuntimeError(f"RapidAPI Booking.com error {resp.status_code}: {resp.text}")

    results = (resp.json() or {}).get("data") or []
    if not results:
        raise ValueError(f"Could not resolve a Booking.com destination for '{query}'.")

    best = results[0]
    return {
        "dest_id": best["dest_id"],
        "search_type": best.get("search_type", "CITY"),
        "name": best.get("name", query),
    }


def search_hotels(dest_id: str, search_type: str, check_in: str, check_out: str,
                   adults: int, max_results: int = 5) -> list[dict]:
    """Search real hotel offers via the RapidAPI Booking.com (DataCrawler) API.

    Returns a list of {"hotel_name", "total_price", "currency"}. Raises on
    API failure instead of returning fabricated data.
    """
    resp = requests.get(
        f"{BASE_URL}/searchHotels",
        headers=_headers(),
        params={
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": check_in,
            "departure_date": check_out,
            "adults": adults,
            "room_qty": 1,
            "currency_code": "USD",
            "languagecode": "en-us",
        },
        timeout=20,
    )
    if not resp.ok:
        raise RuntimeError(f"RapidAPI Booking.com error {resp.status_code}: {resp.text}")

    raw_hotels = ((resp.json() or {}).get("data") or {}).get("hotels") or []

    offers = []
    for entry in raw_hotels[:max_results]:
        prop = entry.get("property") or {}
        price = (prop.get("priceBreakdown") or {}).get("grossPrice") or {}
        name = prop.get("name")
        if not name or price.get("value") is None:
            continue
        offers.append({
            "hotel_name": name,
            "total_price": float(price["value"]),
            "currency": price.get("currency", "USD"),
        })

    return offers
