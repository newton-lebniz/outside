import json
from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, asin, sqrt

import httpx

from .config import EVENTS_PATH, DEFAULT_LAT, DEFAULT_LON, DEFAULT_PLACE

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

WMO = {
    0: "clear", 1: "clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle", 56: "drizzle", 57: "drizzle",
    61: "rain", 63: "rain", 65: "rain", 66: "rain", 67: "rain",
    71: "snow", 73: "snow", 75: "snow", 77: "snow", 85: "snow", 86: "snow",
    80: "rain", 81: "rain", 82: "rain",
    95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm",
}

SIM_PRESETS = {
    "clear":  {"condition": "clear",    "cloud_cover": 5,   "precipitation_mm": 0.0},
    "cloudy": {"condition": "overcast", "cloud_cover": 92,  "precipitation_mm": 0.0},
    "rain":   {"condition": "rain",      "cloud_cover": 100, "precipitation_mm": 2.5},
    "hot":    {"condition": "clear",    "cloud_cover": 10,  "precipitation_mm": 0.0, "temp_c": 36.0},
}


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi = p2 - p1
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * r * asin(sqrt(a))


def is_wet(weather):
    return weather["condition"] in (
        "drizzle", "rain", "thunderstorm", "snow"
    ) or weather["precipitation_mm"] > 0.1


def daypart(hour):
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 20:
        return "evening"
    return "night"


def load_events():
    with open(EVENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def nearest_event(lat, lon, now, events=None, max_km=5.0, window_hours=36):
    """Closest upcoming event inside the distance and time window, or None."""
    events = load_events() if events is None else events
    best = None

    for e in events:
        start = datetime.fromisoformat(e["start"]).replace(tzinfo=now.tzinfo)
        hours_until = (start - now).total_seconds() / 3600

        if hours_until < -0.5 or hours_until > window_hours:
            continue

        dist = haversine_km(lat, lon, e["lat"], e["lon"])

        if dist > max_km:
            continue

        if best is None or dist < best["distance_km"]:
            best = {
                **e,
                "distance_km": round(dist, 1),
                "walk_minutes": round(dist * 12),
                "starts_in_minutes": int(hours_until * 60),
            }

    return best


def assemble_context(
    now,
    lat,
    lon,
    place,
    weather,
    sunrise,
    sunset,
    event,
    completed_types,
    interests,
    prefers_short,
):
    """Pure function: no network. Easy to unit test with fake inputs."""

    is_day = sunrise <= now <= sunset
    minutes_to_sunset = int((sunset - now).total_seconds() / 60)

    weather = {**weather, "is_day": is_day}

    return {
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
        "daypart": daypart(now.hour),
        "location": {
            "name": place,
            "lat": lat,
            "lon": lon,
        },
        "weather": weather,
        "sky": {
            "sunset": sunset.strftime("%H:%M"),
            "minutes_to_sunset": minutes_to_sunset,
        },
        "nearby_event": event,
        "today": {
            "completed_types": list(completed_types),
        },
        "user": {
            "interests": list(interests),
            "prefers_short": prefers_short,
        },
    }


def fetch_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,weather_code,cloud_cover,"
            "wind_speed_10m,precipitation"
        ),
        "daily": "sunrise,sunset",
        "timezone": "auto",
        "forecast_days": 1,
    }

    r = httpx.get(OPEN_METEO, params=params, timeout=15)
    r.raise_for_status()

    return r.json()


def build_context(
    lat=DEFAULT_LAT,
    lon=DEFAULT_LON,
    place=DEFAULT_PLACE,
    interests=None,
    completed_types=None,
    prefers_short=True,
    sim_weather=None,
    sim_time=None,
):
    """Real context: live weather from Open-Meteo. sim_* args are for demos/tests."""

    data = fetch_weather(lat, lon)

    tz = timezone(timedelta(seconds=data["utc_offset_seconds"]))
    now = datetime.now(tz)

    if sim_time:
        h, m = map(int, sim_time.split(":"))
        now = now.replace(hour=h, minute=m, second=0, microsecond=0)

    cur = data["current"]

    weather = {
        "condition": WMO.get(cur["weather_code"], "clear"),
        "temp_c": cur["temperature_2m"],
        "cloud_cover": cur["cloud_cover"],
        "wind_kmh": cur["wind_speed_10m"],
        "precipitation_mm": cur["precipitation"],
    }

    if sim_weather:
        weather.update(SIM_PRESETS[sim_weather])

    sunrise = datetime.fromisoformat(
        data["daily"]["sunrise"][0]
    ).replace(tzinfo=tz)

    sunset = datetime.fromisoformat(
        data["daily"]["sunset"][0]
    ).replace(tzinfo=tz)

    event = nearest_event(lat, lon, now)

    return assemble_context(
        now,
        lat,
        lon,
        place,
        weather,
        sunrise,
        sunset,
        event,
        completed_types or [],
        interests or [],
        prefers_short,
    )
