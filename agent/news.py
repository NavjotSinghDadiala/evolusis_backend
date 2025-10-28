import os
import requests
from loguru import logger

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# fetching top news articles based on a topic -------------------------------
def fetch_news(topic: str, timeout: int = 8) -> dict:
    if not NEWS_API_KEY:
        return {"ok": False, "error": "News API key not configured."}
    try:
        url = f"{NEWS_API_URL}?q={requests.utils.requote_uri(topic)}&language=en&sortBy=publishedAt&pageSize=3&apiKey={NEWS_API_KEY}"
        resp = requests.get(url, timeout=timeout)
        data = resp.json()
        if resp.status_code != 200:
            msg = data.get("message", f"HTTP {resp.status_code}")
            return {"ok": False, "error": f"News API error: {msg}"}

        articles = data.get("articles", [])
        if not articles:
            return {"ok": False, "error": "No news articles found."}

        summaries = []
        for art in articles[:3]:
            title = art.get("title")
            source = art.get("source", {}).get("name")
            url = art.get("url")
            if title and source:
                summaries.append(f"📰 {title} — {source} ({url})")
        summary_text = "\n".join(summaries)
        return {"ok": True, "text": summary_text, "data": articles}
    except Exception as e:
        logger.exception("News API error")
        return {"ok": False, "error": str(e)}