from datetime import datetime, timedelta

from agents import activity_agent, budget_agent, flight_agent, hotel_agent
from services import groq_client
from services.geocode import geocode_city

REQUIRED_FIELDS = ["origin_city", "destination_city", "start_date", "duration_days"]

EXTRACTION_PROMPT = """You are the manager agent of a travel-planning assistant.
Extract a structured trip request from the user's message below.

Today's date is {today} (YYYY-MM-DD). Resolve any relative date expressions
("next week", "tuần tới", "tuần sau", "ngày mai", etc.) into an absolute
start_date in YYYY-MM-DD format, relative to today.

The user may write in Vietnamese or English.

Return ONLY a JSON object with this exact shape, no extra commentary:
{{
  "origin_city": string or null,
  "destination_city": string or null,
  "start_date": "YYYY-MM-DD" or null,
  "duration_days": integer or null,
  "travelers": integer,
  "missing": [list of field names among "origin_city", "destination_city",
              "start_date", "duration_days" that could NOT be determined
              from the message]
}}

Rules:
- "travelers" defaults to 1 if the message does not specify a number of people.
- Never guess origin_city, destination_city, start_date, or duration_days --
  if the message truly does not say, set the field to null and list it in "missing".
- duration_days must be a whole number of days, not a date range.

Previously known fields (from earlier turns in this conversation, may be empty): {known}

User message: "{message}"
"""


def extract_trip_request(user_text: str, known: dict | None = None) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = EXTRACTION_PROMPT.format(today=today, known=known or {}, message=user_text)
    result = groq_client.generate_json(prompt)

    for field in REQUIRED_FIELDS:
        result.setdefault(field, None)
    result.setdefault("travelers", 1)
    result.setdefault("missing", [])

    if known:
        for field in REQUIRED_FIELDS:
            if result.get(field) in (None, "") and known.get(field) not in (None, ""):
                result[field] = known[field]

    result["missing"] = [f for f in REQUIRED_FIELDS if result.get(f) in (None, "")]
    return result


def plan_trip(trip: dict) -> dict:
    """Call every specialist agent with the confirmed trip request and combine
    their real API results into a single itinerary. Each agent's failure is
    captured independently so a partial plan can still be shown."""
    origin_city = trip["origin_city"]
    destination_city = trip["destination_city"]
    start_date = trip["start_date"]
    duration_days = int(trip["duration_days"])
    travelers = int(trip.get("travelers") or 1)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=duration_days)
    return_date = end_dt.strftime("%Y-%m-%d")

    result = {
        "request": trip,
        "return_date": return_date,
        "flights": None,
        "hotels": None,
        "activities": None,
        "budget": None,
        "errors": [],
    }

    try:
        result["flights"] = flight_agent.search_flights(
            origin_city, destination_city, start_date, return_date, travelers
        )
    except Exception as exc:
        result["errors"].append(f"Flight agent: {exc}")

    try:
        result["hotels"] = hotel_agent.search_hotels(
            destination_city, start_date, return_date, travelers
        )
    except Exception as exc:
        result["errors"].append(f"Hotel agent: {exc}")

    try:
        place = geocode_city(destination_city)
        result["activities"] = activity_agent.search_activities(
            place["latitude"], place["longitude"]
        )
    except Exception as exc:
        result["errors"].append(f"Activity agent: {exc}")

    cheapest_flight = None
    flights = result["flights"]
    if flights:
        cheapest_out = (
            min(flights["outbound_offers"], key=lambda o: o["price"])
            if flights["outbound_offers"] else None
        )
        cheapest_in = (
            min(flights["inbound_offers"], key=lambda o: o["price"])
            if flights["inbound_offers"] else None
        )
        if cheapest_out:
            per_person = cheapest_out["price"] + (cheapest_in["price"] if cheapest_in else 0)
            cheapest_flight = {
                "total_price": per_person * travelers,
                "currency": "USD",
                "outbound": cheapest_out,
                "inbound": cheapest_in,
                # A return trip was requested but no cached return-leg price
                # was found, so this total only covers the outbound leg.
                "missing_return_leg": flights["return_requested"] and cheapest_in is None,
            }

    cheapest_hotel = None
    if result["hotels"] and result["hotels"]["offers"]:
        priced = [o for o in result["hotels"]["offers"] if o["total_price"] is not None]
        cheapest_hotel = min(priced, key=lambda o: o["total_price"]) if priced else None

    result["budget"] = budget_agent.calculate_budget(
        cheapest_flight, cheapest_hotel, duration_days, travelers
    )
    result["cheapest_flight"] = cheapest_flight
    result["cheapest_hotel"] = cheapest_hotel

    return result
