from fastapi import FastAPI, File, UploadFile, Response
from fastapi.responses import StreamingResponse , FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from collections import deque
import io
import base64
import tempfile
from elevenlabs import ElevenLabs

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse



load_dotenv()

import google.generativeai as genai
from agent.weather import *           # importing everything from weather.py        
from agent.news import *              # importing everything from news.py
from loguru import logger
import time

logger.add("agent.log", rotation="5 MB", retention="7 days")

GEN_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEN_API_KEY:
    print(" GEMINI_API_KEY not set in .env")
else:
    genai.configure(api_key=GEN_API_KEY)
    print(" Gemini API configured successfully")

try:
    model = genai.GenerativeModel("models/gemini-2.5-flash")
except Exception:
    model = genai.GenerativeModel("models/gemini-flash-latest")

#-------------------------------------------------------- API KEY --------------------------------------------------------
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

#-------------------------------------- Just to check if the API keys are working or not (FALLBACK)--------------------------------------------
if WEATHER_API_KEY:
    print(" Weather API key loaded successfully")
else:
    print(" WEATHER_API_KEY not found")

if NEWS_API_KEY:
    print(" News API key loaded successfully")
else:
    print(" NEWS_API_KEY not found")

app = FastAPI(title="AI Agent with Gemini + Weather + News")

# Short-term memory: Store last 5 queries with timestamps
memory = deque(maxlen=5)

class QueryRequest(BaseModel):
    query: str


# ---------------------------------------------------- MEMORY FUNCTIONS -----------------------------------------------------------------

def add_to_memory(query: str):
    memory.append(query)

def get_memory_context() -> str:
    if not memory:
        return "No previous queries in this session"
    
    context = "Previous queries in this conversation:\n"
    for idx, query in enumerate(reversed(list(memory)), 1):
        context += f"{idx}. {query}\n"
    return context


# ---------------------------------------------- LLM COMBINE -----------------------------------------------------------------


def ask_llm_for_combined_answer(query: str, factual_text: str | None, info_type: str = "general") -> str:
    memory_context = get_memory_context()     # Giving memory context
    
    if info_type == "weather":
        base_prompt = (
            "You are a helpful assistant. The user asked a question about the weather.\n"
            "Use the following factual weather data to generate a short, conversational answer."
        )
    elif info_type == "news":
        base_prompt = (
            "You are an AI assistant. The user asked for news or updates.\n"
            "Summarize the factual news items given below into a natural, coherent answer."
        )
    else:
        base_prompt = "You are a helpful assistant answering general questions."

    user_context = f"""{memory_context}

Current user query: "{query}"

Factual data (from API):
{factual_text or 'No factual data available.'}

Please provide a clear answer (2 or 4 sentences). If the user refers to something from previous queries (like "that place", "it", "there"), use the context from previous queries to understand what they mean."""

    try:
        resp = model.generate_content(f"{base_prompt}\n\n{user_context}", request_options={"timeout": 15})
        return (resp.text or "").strip()
    except Exception as e:
        logger.exception("LLM error combining factual data")
        return "Sorry, I could not generate a complete answer right now."


# ----------------------------------------------------------------- ROUTES -----------------------------------------------------------------

@app.post("/ask")
async def ask(req: QueryRequest):
    query = (req.query or "").strip()
    if not query:
        return {"error": "Please provide a non-empty query."}

    add_to_memory(query)                                       # Adding query to short-term memory
    logger.info(f"Added query to memory. Total queries in memory: {len(memory)}")

    q_lower = query.lower()
    t0 = time.time()

    try:
# --- WEATHER PART ----------------------
        if any(word in q_lower for word in ("weather", "temperature", "rain", "snow", "forecast")):
            reasoning = "Detected weather-related query. Fetching weather data..."
            logger.info(f"Weather intent detected for query: '{query}'")
            city = None
            if " in " in q_lower:
                city = q_lower.split(" in ", 1)[1].replace("today", "").replace("now", "").strip(" ?.")
            if not city:
                logger.warning("Weather query detected but no city specified")
                return {
                    "reasoning": "Weather query detected but no city found.",
                    "answer": "Please specify the city you'd like the weather for."
                }

            logger.info(f"Fetching weather for city: '{city}'")
            weather = fetch_weather(city)
            if weather["ok"]:
                logger.info(f"Weather fetch successful for {city}")
                answer = ask_llm_for_combined_answer(query, weather["text"], info_type="weather")
            else:
                logger.warning(f"Weather fetch failed for {city}: {weather.get('error')}")
                answer = ask_llm_for_combined_answer(query, weather["error"], info_type="weather")

            logger.info(f"Processed weather query in {time.time()-t0:.2f}s | city={city}")
            return {"reasoning": reasoning, "answer": answer}

# --- NEWS PART ----------------------
        elif any(word in q_lower for word in ("news", "headline", "update", "report")):
            reasoning = "Detected news-related query. Fetching news articles..."
            logger.info(f"News intent detected for query: '{query}'")
            topic = q_lower.replace("news about", "").replace("latest news on", "").replace("news", "").strip(" ?.")
            if not topic:
                topic = "general"
            logger.info(f"Fetching news for topic: '{topic}'")
            news = fetch_news(topic)
            if news["ok"]:
                logger.info(f"News fetch successful for topic: {topic}")
                answer = ask_llm_for_combined_answer(query, news["text"], info_type="news")
            else:
                logger.warning(f"News fetch failed for {topic}: {news.get('error')}")
                answer = ask_llm_for_combined_answer(query, news["error"], info_type="news")

            logger.info(f"Processed news query in {time.time()-t0:.2f}s | topic={topic}")
            return {"reasoning": reasoning, "answer": answer}

# --- GENERAL PART -----------
        else:
            reasoning = "Detected general question. Responding via Gemini."
            logger.info(f"General intent detected for query: '{query}'")
            memory_context = get_memory_context()
            logger.info(f"Memory context: {memory_context}")
            prompt = f"""You are a helpful assistant in an ongoing conversation. 

{memory_context}

Current user query: "{query}"

Please answer the user's question. IMPORTANT: If the user is referring to something from previous queries (like "that place", "it", "there", etc.), use the context from the previous queries to understand what they're talking about."""
            resp = model.generate_content(prompt, request_options={"timeout": 12})
            answer = (resp.text or "").strip()
            logger.info(f"Processed general query in {time.time()-t0:.2f}s")
            return {"reasoning": reasoning, "answer": answer}

    except Exception as e:
        logger.exception("Unhandled error in /ask")
        return {"error": f"Internal error: {e}"}

#----------------------------------------------------- MEMORY ROUTES -----------------------------------------------------------------
#--------------Get the current short-term memory (last 5 queries)------
@app.get("/memory")
async def get_memory():
    return {
        "memory": list(memory),
        "count": len(memory)
    }

#------------------------------ Clear the short-term memory ---------------
@app.post("/memory/clear")
async def clear_memory():
    global memory
    memory.clear()
    logger.info("Short-term memory cleared")
    return {"message": "Memory cleared successfully"}








