# 🤖 AI Agent — Gemini + Weather + News

An intelligent conversational agent built with **FastAPI** and **Google Gemini**, capable of understanding queries, **planning its next steps**, and **using external APIs** (Weather + News) to provide real-time, human-like responses.

---

## 🧭 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Design & Implementation Approach](#design--implementation-approach)
- [How the Solution Works](#how-the-solution-works)
- [APIs Used and Why](#apis-used-and-why)
- [Tech Stack](#tech-stack)
- [Setup & Running](#setup--running)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Demo Video](#demo-video)
- [Notes](#notes)

---

## 🧠 Overview
This project showcases an **AI Agent** that doesn’t just respond — it **thinks, plans, and executes**.  
The system is built over a **FastAPI backend**, with **Gemini** as the core reasoning model, and integrates live data from **Weather** and **News** APIs.

It uses short-term memory to maintain context and respond naturally in multi-turn conversations.

---

## ✨ Features
- 🧩 Understands user intent (General / Weather / News).
- 🧠 Uses **Gemini** to plan and decide actions before responding.
- ☁️ Fetches real-time data using **OpenWeatherMap** and **NewsAPI**.
- 🧵 Maintains **short-term memory** (last 10 queries).
- 💬 Generates natural, context-aware, human-like answers.
- 🧾 Simple REST API interface via `/docs` (Swagger UI).

---

## 🧩 Design & Implementation Approach

This project follows a **Planner–Executor–LLM** design:

```text
User → Planner (Gemini decides next steps)
     → Executor (fetches data via APIs)
     → Gemini (combines facts + context)
     → Final Natural Reply
```

🔹 Step 1: Planner (Gemini)
Gemini receives the user query + memory context and generates a JSON plan.
It decides whether to call a weather API, news API, or just reply directly.

🔹 Step 2: Executor
Executes the plan:

Fetches live data from APIs (Weather or News).

Collects “observations” — factual snippets.

🔹 Step 3: LLM Combiner
Gemini combines these observations and past context into a short, conversational reply.

🔹 Step 4: Memory
A short-term deque memory remembers the last 10 queries to maintain flow.

---

## ⚙️ How the Solution Works
User sends a JSON request to:

```json
POST /ask
{
  "query": "What's the weather in Paris today?"
}
```
The backend:

- Adds the query to memory.
- Sends it to Gemini which plans actions.
- Executes API calls if required.
- Combines real data + Gemini reasoning → reply.

Returns:

```json
{
  "reasoning": "Used: Weather API",
  "apis": ["weather"],
  "answer": "The weather in Paris is sunny with a high of 21°C today."
}
```

---

## 🌐 APIs Used and Why

| API | Purpose | Why Used |
|-----|---------|----------|
| Google Gemini (Generative AI) | Core LLM for reasoning, planning, and generating replies. | Provides intelligent, contextual, and natural-language understanding. |
| OpenWeatherMap API | Fetches live weather data for any city. | Ensures factual and up-to-date weather responses. |
| NewsAPI | Retrieves top headlines and summaries. | Adds real-time news content to the agent’s responses. |

---

## 🧰 Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Framework | FastAPI |
| LLM | Google Gemini (`google-generativeai`) |
| APIs | OpenWeatherMap, NewsAPI |
| Server | Uvicorn |
| Logging | Loguru |
| HTTP | requests |

---

## 🚀 Setup & Running
Follow these steps to run the project locally 👇

### 1. Clone the Repository
```bash
git clone https://github.com/NavjotSinghDadiala/evolusis_backend.git
cd evolusis_backend
```

### 2. Create a Virtual Environment (Windows - PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add:

```env
GEMINI_API_KEY=your_gemini_api_key_here
WEATHER_API_KEY=your_openweather_api_key_here
NEWS_API_KEY=your_newsapi_key_here
```

### 5. Run the Application
```bash
uvicorn main:app --reload
```

### 6. Open Swagger UI
Visit: http://127.0.0.1:8000/docs

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /ask | POST | Accepts a user query, plans intelligently, fetches data if needed, and replies naturally. |
| /memory | GET | Displays the last 10 remembered user queries. |
| /memory/clear | POST | Clears short-term memory. |

---

## 💬 Usage Examples

```bash
# Example 1 — Weather Query
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in London today?"}'

# Example 2 — News Query
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Latest news about bitcoin"}'

# Example 3 — View Memory
curl http://127.0.0.1:8000/memory

# Example 4 — Clear Memory
curl -X POST http://127.0.0.1:8000/memory/clear
```

---

## 🎥 Demo Video

- Loom Demo: https://www.loom.com/share/dfee246fd59d4c7cb95d657feb73beea

---

## 📝 Notes
- Use Python 3.10 – 3.12.
- Make sure the `.env` file is properly configured.
- Works best with a stable internet connection (APIs are live).

The `/ask` endpoint automatically determines whether to:

- Call Weather API
- Call News API
- Or answer directly using Gemini.

---

## 🧾 Summary
This project demonstrates how an AI Agent can:

- Think using Gemini’s reasoning power
- Decide what APIs to call
- Act by fetching real-time data

It’s a step toward building intelligent, self-planning, API-integrated AI systems that go beyond simple chatbots — blending live data with reasoning.
