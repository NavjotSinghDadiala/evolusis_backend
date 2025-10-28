import os
import requests
from loguru import logger

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


def fetch_weather(city: str, timeout: int = 8) -> dict:
    if not WEATHER_API_KEY:
        return {"ok": False, "error": "Weather API key not configured."}

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?"
            f"q={requests.utils.requote_uri(city)}&appid={WEATHER_API_KEY}&units=metric"
        )
        resp = requests.get(url, timeout=timeout)
        data = resp.json()
        if resp.status_code != 200:
            msg = data.get("message", f"HTTP {resp.status_code}")
            return {"ok": False, "error": f"Weather API error: {msg}"}

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        humidity = data["main"].get("humidity")
        wind = data.get("wind", {}).get("speed")
        human_text = (
            f"{city.title()}: {temp}°C, {desc}."
            + (f" Humidity: {humidity}%." if humidity is not None else "")
            + (f" Wind speed: {wind} m/s." if wind is not None else "")
        )
        return {"ok": True, "text": human_text, "data": data}

    except Exception as e:
        logger.exception("Weather API error")
        return {"ok": False, "error": str(e)}