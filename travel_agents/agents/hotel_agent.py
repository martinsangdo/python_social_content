from services.rapidapi_hotels_client import resolve_destination, search_hotels as _search_hotels


def search_hotels(city_name: str, check_in: str, check_out: str, adults: int,
                   max_results: int = 5) -> dict:
    """Search real hotel offers via the RapidAPI Booking.com (DataCrawler) API.

    Returns {"city_name", "offers": [...]}. Raises on lookup/API failure
    instead of returning fabricated data.
    """
    destination = resolve_destination(city_name)

    raw_offers = _search_hotels(
        destination["dest_id"], destination["search_type"], check_in, check_out,
        adults, max_results,
    )

    offers = [
        {
            "hotel_name": offer["hotel_name"],
            "total_price": offer["total_price"],
            "currency": offer["currency"],
            "check_in": check_in,
            "check_out": check_out,
        }
        for offer in raw_offers
    ]

    return {"city_name": destination["name"], "offers": offers}
