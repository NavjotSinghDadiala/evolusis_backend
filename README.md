## AI Agent — concise guide

Table of Contents
- Features
- How my solution works
- Tech Stack
- Running the Application
- API Endpoints and why
- Usage (examples)
- Screenshots
- Demo Video

Features
- Simple chat endpoint that answers general, news, and weather questions.
- Short-term memory: remembers the last 5 queries to keep context.
- Uses live data for weather and news when needed.

How my solution works
- You send a JSON query to `POST /ask`.
- The app checks the text for keywords. If it looks like a weather or news question, it calls the matching API to get facts. Otherwise it asks the LLM (Gemini) directly.
- The app then asks Gemini to combine the facts and the recent memory into a short, friendly reply.

Tech Stack
- Python 3.10+
- FastAPI 
- Uvicorn 
- google-generativeai (Gemini LLM)
- requests (HTTP calls to External APIs)
- loguru (logging)

Running the Application
1. Create and activate a virtual env (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Install deps and run:
```powershell
pip install -r requirements.txt
uvicorn main:app --reload
```
Server runs at: http://127.0.0.1:8000

Environment variables (required)
- `GEMINI_API_KEY` — Google Generative AI key
- `WEATHER_API_KEY` — OpenWeatherMap key
- `NEWS_API_KEY` — NewsAPI key

API Endpoints and why
- POST /ask
	- Input: { "query": "your question" }
	- Purpose: single conversational entry. Detects intent (weather/news/general) and returns a short answer combining facts and context.
- GET /memory
	- Purpose: view the last 5 user queries (helps debugging or UX).
- POST /memory/clear
	- Purpose: clear short-term memory.

Usage (examples)
```powershell
curl -X POST "http://127.0.0.1:8000/ask" -H "Content-Type: application/json" -d '{"query":"What's the weather in London today?"}'

curl -X POST "http://127.0.0.1:8000/ask" -H "Content-Type: application/json" -d '{"query":"Latest news about bitcoin"}'

curl http://127.0.0.1:8000/memory
curl -X POST http://127.0.0.1:8000/memory/clear
```

Demo Video
- Add a short demo video file or a YouTube link here. Example: `docs/demo.mp4` or `https://youtu.be/your-demo-link`.

Notes
- Use Python version between 3.10 or 3.12
- Make sure the required API keys are set in your environment or `.env`.


