from services.travelpayouts_client import resolve_place, search_one_way_prices


def _format_offers(raw_offers: list[dict]) -> list[dict]:
    offers = []
    for offer in raw_offers:
        price = offer.get("price")
        if price is None:
            continue
        offers.append({
            "price": float(price),
            "currency": "USD",
            "airline": offer.get("airline"),
            "flight_number": offer.get("flight_number"),
            "departure_at": offer.get("departure_at"),
            "transfers": offer.get("transfers"),
            "link": f"https://www.aviasales.com{offer['link']}" if offer.get("link") else None,
        })
    return offers


def _search_leg(origin_iata: str, destination_iata: str, date: str, limit: int) -> tuple[list[dict], bool]:
    """Try the exact requested date first; the Aviasales cache only holds
    what users searched in the last 48h, so an exact day is often empty.
    Fall back to the whole month and say so, rather than silently
    substituting a different date without telling the caller."""
    raw = search_one_way_prices(origin_iata, destination_iata, date, limit)
    if raw:
        return _format_offers(raw), True

    month = date[:7]
    raw = search_one_way_prices(origin_iata, destination_iata, month, limit * 3)
    return _format_offers(raw), False


def search_flights(origin_city: str, destination_city: str, depart_date: str,
                    return_date: str | None, adults: int, max_results: int = 10) -> dict:
    """Search real one-way flight prices (per leg) via the Aviasales/
    Travelpayouts Data API. Round trips are two independent one-way
    searches -- combined round-trip cache queries were found to return
    almost no results for real routes/dates.

    Returns {"origin_airport", "destination_airport", "outbound_offers",
    "outbound_exact_date", "inbound_offers", "inbound_exact_date"}.
    Prices are per traveler; multiply by `adults` for the group total.
    Raises on lookup/API failure instead of returning fabricated data.
    """
    origin = resolve_place(origin_city)
    destination = resolve_place(destination_city)

    outbound_offers, outbound_exact = _search_leg(
        origin["iataCode"], destination["iataCode"], depart_date, max_results
    )

    inbound_offers, inbound_exact = [], True
    if return_date:
        inbound_offers, inbound_exact = _search_leg(
            destination["iataCode"], origin["iataCode"], return_date, max_results
        )

    return {
        "origin_airport": origin["iataCode"],
        "destination_airport": destination["iataCode"],
        "outbound_offers": outbound_offers,
        "outbound_exact_date": outbound_exact,
        "inbound_offers": inbound_offers,
        "inbound_exact_date": inbound_exact,
        "return_requested": bool(return_date),
    }
