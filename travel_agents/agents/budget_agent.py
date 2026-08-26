def calculate_budget(cheapest_flight: dict | None, cheapest_hotel: dict | None,
                      nights: int, travelers: int) -> dict:
    """Combine real prices returned by the flight/hotel agents into a budget.

    Only sums numbers actually returned by the upstream APIs -- if a price is
    missing, it is reported as unavailable rather than estimated.
    """
    breakdown = []
    total = 0.0
    currency = None
    complete = True

    if cheapest_flight and cheapest_flight.get("total_price") is not None:
        trip_type = "one-way only, no return price found" if cheapest_flight.get(
            "missing_return_leg"
        ) else "round trip"
        breakdown.append({
            "item": f"Flights ({travelers} traveler(s), {trip_type})",
            "amount": cheapest_flight["total_price"],
            "currency": cheapest_flight["currency"],
        })
        total += cheapest_flight["total_price"]
        currency = cheapest_flight["currency"]
        if cheapest_flight.get("missing_return_leg"):
            complete = False
    else:
        complete = False
        breakdown.append({"item": "Flights", "amount": None, "currency": None})

    if cheapest_hotel and cheapest_hotel.get("total_price") is not None:
        breakdown.append({
            "item": f"Hotel ({nights} night(s), 1 room)",
            "amount": cheapest_hotel["total_price"],
            "currency": cheapest_hotel["currency"],
        })
        total += cheapest_hotel["total_price"]
        currency = currency or cheapest_hotel["currency"]
    else:
        complete = False
        breakdown.append({"item": "Hotel", "amount": None, "currency": None})

    return {
        "breakdown": breakdown,
        "total": total,
        "currency": currency,
        "complete": complete,
        "note": (
            "Activities are shown separately: OpenStreetMap does not provide ticket "
            "pricing, so no cost is estimated for them."
        ),
    }
