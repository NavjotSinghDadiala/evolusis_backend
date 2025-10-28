from fastapi import FastAPI, File, UploadFile, Response
from fastapi.responses import StreamingResponse , FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from collections import deque
load_dotenv()

import google.generativeai as genai
from agent.weather import *           # importing everything from weather.py        
from agent.news import *              # importing everything from news.py
from loguru import logger
import time
import json

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

memory = deque(maxlen=10)

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


# ---------------------------------------------- LLM COMBINE ----------------------------------------------------


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


# -------------------- Planner and Executor helpers --------------------------------------
def generate_plan_from_llm(query: str, memory_context: str, timeout: int = 12) -> dict | None:
    planner_prompt = f"""
You are an agent planner. Output ONLY valid JSON with the following shape:
{{
  "plan": [
    {{"action": "fetch_weather", "params": {{"city": "<city>"}}}},
    {{"action": "fetch_news", "params": {{"topic": "<topic>"}}}},
    {{"action": "reply", "params": {{"tone": "short"}}}}
  ],
  "explain": "short human readable explanation"
}}

Allowed actions: fetch_weather(city), fetch_news(topic), reply()
Use the memory below to help pick actions. Fill params (city/topic) when needed.

Memory:
{memory_context}

Current user query: "{query}"

Produce only valid JSON. Do not output any other text.
"""
    try:
        resp = model.generate_content(planner_prompt, request_options={"timeout": timeout})
        text = (resp.text or "").strip()
        try:
            plan = json.loads(text)
            if isinstance(plan, dict) and "plan" in plan:
                return plan
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    plan = json.loads(text[start:end+1])
                    if isinstance(plan, dict) and "plan" in plan:
                        return plan
                except Exception:
                    logger.warning("Planner produced non-JSON output")
        return None
    except Exception:
        logger.exception("Planner LLM error")
        return None

#-----Execute actions in the plan .. It collects factual outputs and then asks the LLM to craft a reply.
def execute_plan(plan: dict, query: str) -> dict:
    actions = plan.get("plan", []) if isinstance(plan, dict) else []
    observations = []
    info_type = "general"
    used_apis = set()

    for step in actions:
        if not isinstance(step, dict):
            continue
        action = step.get("action")
        params = step.get("params") or {}

        if action == "fetch_weather":
            city = params.get("city")
            if not city:
                observations.append("fetch_weather skipped: no city provided.")
                continue
            logger.info(f"Executor: fetching weather for {city}")
            res = fetch_weather(city)
            if res.get("ok"):
                observations.append(res.get("text"))
                info_type = "weather"
                used_apis.add("weather")
            else:
                observations.append(f"weather error: {res.get('error')}")

        elif action == "fetch_news":
            topic = params.get("topic")
            if not topic:
                observations.append("fetch_news skipped: no topic provided.")
                continue
            logger.info(f"Executor: fetching news for {topic}")
            res = fetch_news(topic)
            if res.get("ok"):
                observations.append(res.get("text"))
                if info_type != "weather":
                    info_type = "news"
                used_apis.add("news")
            else:
                observations.append(f"news error: {res.get('error')}")

        elif action == "reply":
            factual_text = "\n".join(observations) if observations else None
            logger.info("Executor: finalizing reply via LLM")
            answer = ask_llm_for_combined_answer(query, factual_text, info_type=info_type)
# build reasoning
            if used_apis:
                reasoning_parts = []
                if "weather" in used_apis:
                    reasoning_parts.append("Weather API")
                if "news" in used_apis:
                    reasoning_parts.append("News API")
                reasoning = "Used: " + ", ".join(reasoning_parts)
            else:
                reasoning = "general"
            return {"ok": True, "answer": answer, "reasoning": reasoning, "details": {"observations": observations}}

        else:
            observations.append(f"unknown action: {action}")

    factual_text = "\n".join(observations) if observations else None
    answer = ask_llm_for_combined_answer(query, factual_text, info_type=info_type)
    if used_apis:
        reasoning_parts = []
        if "weather" in used_apis:
            reasoning_parts.append("Weather API")
        if "news" in used_apis:
            reasoning_parts.append("News API")
        reasoning = "Used: " + ", ".join(reasoning_parts)
    else:
        reasoning = "general"
    return {"ok": True, "answer": answer, "reasoning": reasoning, "details": {"observations": observations}}



# ------------------------------ ROUTES --------------------------------------------------------

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
        memory_context = get_memory_context()
        plan = generate_plan_from_llm(query, memory_context)
        if plan:
            logger.info("Planner returned a valid plan, executing...")
            exec_result = execute_plan(plan, query)
            logger.info(f"Executed plan in {time.time()-t0:.2f}s")
            # classify final reasoning: general vs api-triggered
            plan_reasoning = exec_result.get("reasoning", "general")
            apis = []
            if isinstance(plan_reasoning, str) and plan_reasoning.startswith("Used:"):
                # extract API names
                used = plan_reasoning.split("Used:", 1)[1].strip()
                for part in [p.strip() for p in used.split(",") if p.strip()]:
                    if part.lower().startswith("weather"):
                        apis.append("weather")
                    elif part.lower().startswith("news"):
                        apis.append("news")
                    else:
                        apis.append(part)
                classification = "fetched via external api"
            else:
                classification = "general LLM used ie Gemini"
            return {"reasoning": classification, "apis": apis, "answer": exec_result.get("answer"), "details": exec_result.get("details")}

# Fallback if it doesnt understands 
        logger.info("Planner failed or returned invalid output — falling back to previous reactive behavior")
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
            return {"reasoning": "api", "apis": ["weather"], "answer": answer}

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
            return {"reasoning": "api", "apis": ["news"], "answer": answer}

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
            return {"reasoning": "general", "apis": [], "answer": answer}

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








