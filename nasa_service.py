"""
NASA API integration layer.

Responsible for:
- external API calls
- data parsing and formatting
- error handling
"""

import random
import requests
from datetime import datetime, timezone, timedelta

NASA_BASE_URL = "https://api.nasa.gov"
NASA_IMAGE_LIBRARY_URL = "https://images-api.nasa.gov/search"

# ================= CORE HELPER =================

def get_nasa_json(api_key, endpoint, params=None):
    # Generic helper for NASA endpoints

    request_params = params or {}
    request_params["api_key"] = api_key

    try:
        response = requests.get(
            f"{NASA_BASE_URL}{endpoint}",
            params=request_params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as error:
        return None, str(error)

# ================= APOD =================

def fetch_apod_data(api_key):
    # Fetch Astronomy Picture of the Day

    data, error = get_nasa_json(api_key, "/planetary/apod")
    if error:
        return {"error": "Could not load APOD data right now."}

    return {
        "title": data.get("title"),
        "date": data.get("date"),
        "description": data.get("explanation"),
        "url": data.get("url"),
        "media_type": data.get("media_type"),
    }

# ================= MARS =================

def fetch_mars_data(api_key):
    # Fetch Mars weather data

    data, error = get_nasa_json(
        api_key,
        "/insight_weather/",
        {"feedtype": "json", "ver": "1.0"},
    )
    if error:
        return {"error": "Could not load Mars weather right now."}

    sol_keys = data.get("sol_keys", [])
    if not sol_keys:
        return {"weather": {}}

    latest_sol = sol_keys[-1]
    latest = data.get(latest_sol, {})

    return {
        "weather": {
            "sol": latest_sol,
            "average_temperature": latest.get("AT", {}).get("av"),
            "wind_speed": latest.get("HWS", {}).get("av"),
            "pressure": latest.get("PRE", {}).get("av"),
            "season": latest.get("Season"),
        }
    }

# ================= NEO =================

def fetch_neo_data(api_key):
    # Fetch near-earth asteroid data

    today = datetime.now(timezone.utc).date()
    next_day = today + timedelta(days=1)

    data, error = get_nasa_json(
        api_key,
        "/neo/rest/v1/feed",
        {
            "start_date": today.isoformat(),
            "end_date": next_day.isoformat(),
        },
    )
    if error:
        return {"error": "Could not load Near Earth Object data right now."}

    objects = data.get("near_earth_objects", {}).get(today.isoformat(), [])[:3]

    result = []
    for asteroid in objects:
        diameter = asteroid.get("estimated_diameter", {}).get("meters", {})
        approach = asteroid.get("close_approach_data", [])

        miss = "Unknown"
        if approach:
            miss = approach[0].get("miss_distance", {}).get("kilometers")

        result.append(
            {
                "name": asteroid.get("name"),
                "diameter": f"{diameter.get('estimated_diameter_min',0):.2f}m - {diameter.get('estimated_diameter_max',0):.2f}m",
                "miss_distance": f"{miss} km",
            }
        )

    return {"asteroids": result}

# ================= DONKI =================

def fetch_donki_data(api_key):
    # Fetch recent CME events

    today = datetime.now(timezone.utc).date()
    past = today - timedelta(days=30)

    data, error = get_nasa_json(
        api_key,
        "/DONKI/CME",
        {"startDate": past.isoformat(), "endDate": today.isoformat()},
    )
    if error:
        return {"error": "Could not load DONKI CME data right now."}

    return {
        "events": [
            {"catalog": e.get("catalog"), "start_time": e.get("startTime")}
            for e in data[:3]
        ]
    }

# ================= IMAGE LIBRARY =================

def fetch_image_library_data():
    # Fetch random moon images from NASA library

    try:
        query = random.choice(
            ["moon", "lunar", "full moon", "moon surface", "moon landing"]
        )
        page = random.randint(1, 10)

        response = requests.get(
            NASA_IMAGE_LIBRARY_URL,
            params={"q": query, "media_type": "image", "page": page},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return {"error": "Could not load NASA Image Library data right now."}

    items = data.get("collection", {}).get("items", [])[:3]

    images = []
    for item in items:
        meta = item.get("data", [{}])[0]
        links = item.get("links", [])
        url = links[0].get("href") if links else None

        images.append(
            {
                "title": meta.get("title"),
                "description": meta.get("description"),
                "url": url,
            }
        )

    return {"images": images}
