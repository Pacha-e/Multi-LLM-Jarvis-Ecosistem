"""J.A.R.V.I.S. — LangChain Tools"""

import math
import json
import httpx
import psutil
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

from jarvis.config import config
from jarvis.agent.memory import JarvisMemory

_memory = JarvisMemory(config.DB_PATH)


@tool
def get_current_datetime() -> str:
    """Get the current date and time."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y — %H:%M:%S")


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city using wttr.in (free, no API key needed).
    Args:
        city: City name (e.g. 'Bogota', 'Medellin', 'New York')
    """
    try:
        # Try wttr.in (free)
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=j1"
        r = httpx.get(url, timeout=8.0)
        if r.status_code == 200:
            data = r.json()
            current = data["current_condition"][0]
            temp_c = current["temp_C"]
            feels_c = current["FeelsLikeC"]
            humidity = current["humidity"]
            desc = current["weatherDesc"][0]["value"]
            wind = current["windspeedKmph"]
            return (
                f"Weather in {city}: {desc}\n"
                f"Temperature: {temp_c}°C (feels like {feels_c}°C)\n"
                f"Humidity: {humidity}% | Wind: {wind} km/h"
            )
    except Exception as e:
        pass

    # Fallback: OpenWeatherMap
    if config.OPENWEATHER_API_KEY:
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            r = httpx.get(url, params={
                "q": city, "appid": config.OPENWEATHER_API_KEY,
                "units": "metric", "lang": "es"
            }, timeout=8.0)
            data = r.json()
            return (
                f"Weather in {city}: {data['weather'][0]['description']}\n"
                f"Temperature: {data['main']['temp']}°C | Humidity: {data['main']['humidity']}%"
            )
        except Exception:
            pass

    return f"Could not get weather for {city}. Check your connection."


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo (free) or Brave API.
    Args:
        query: Search query string
    """
    # Try Brave Search API first
    if config.BRAVE_API_KEY:
        try:
            r = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": config.BRAVE_API_KEY},
                params={"q": query, "count": 5},
                timeout=10.0,
            )
            results = r.json().get("web", {}).get("results", [])
            if results:
                output = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results[:5], 1):
                    output += f"{i}. {r['title']}\n   {r['url']}\n   {r.get('description', '')[:200]}\n\n"
                return output
        except Exception:
            pass

    # Fallback: DuckDuckGo HTML scrape (free, no key)
    try:
        r = httpx.get(
            "https://duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10.0,
            follow_redirects=True,
        )
        # Simple extraction
        import re
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', r.text, re.DOTALL)
        if snippets:
            output = f"Search results for '{query}':\n\n"
            for i, (t, s) in enumerate(zip(titles[:5], snippets[:5]), 1):
                clean_t = re.sub(r'<[^>]+>', '', t).strip()
                clean_s = re.sub(r'<[^>]+>', '', s).strip()
                output += f"{i}. {clean_t}\n   {clean_s}\n\n"
            return output
    except Exception:
        pass

    return f"Could not search for '{query}'. Check your connection."



@tool
def scrape_url(url: str, extract: str = "text") -> str:
    """Scrape a web page and extract its content.
    Args:
        url: Full URL to scrape (e.g. 'https://example.com/article')
        extract: What to extract: 'text' (clean text), 'links' (all links), 'summary' (first 1000 chars)
    """
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        }
        r = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        if extract == "links":
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if href.startswith("http") and text:
                    links.append(f"- {text}: {href}")
            return ("Links from " + url + ":\n" + "\n".join(links[:30])) if links else "No links found."
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        clean = "\n".join(lines)
        if extract == "summary":
            return "Summary of " + url + ":\n" + clean[:1000] + "..."
        return "Content from " + url + ":\n" + clean[:4000]
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code} error scraping {url}"
    except Exception as e:
        return f"Could not scrape {url}: {e}"

@tool
def remember_fact(key: str, value: str, category: str = "general") -> str:
    """Store a fact in long-term memory.
    Args:
        key: Unique identifier for the fact (e.g. 'user_birthday', 'project_name')
        value: The fact to remember
        category: Category for organization (general, personal, work, etc.)
    """
    _memory.remember(key, value, category)
    return f"Remembered: {key} = {value}"


@tool
def recall_fact(key: str) -> str:
    """Retrieve a specific fact from long-term memory.
    Args:
        key: The key to look up
    """
    value = _memory.recall(key)
    if value:
        return f"{key}: {value}"
    return f"No memory found for key '{key}'"


@tool
def search_memory(query: str) -> str:
    """Search long-term memory for relevant information.
    Args:
        query: Search term to find in stored memories
    """
    results = _memory.search_memory(query)
    if not results:
        return f"No memories found matching '{query}'"
    output = f"Memories matching '{query}':\n"
    for r in results:
        output += f"- {r['key']}: {r['value']} [{r['category']}]\n"
    return output


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.
    Args:
        expression: Math expression (e.g. '2 ** 10', 'sqrt(144)', '15 * 7 + 3')
    """
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Could not calculate '{expression}': {e}"


@tool
def get_system_info() -> str:
    """Get current system resource usage (CPU, RAM, disk)."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return (
            f"System Status:\n"
            f"CPU: {cpu}%\n"
            f"RAM: {ram.used / 1e9:.1f}GB / {ram.total / 1e9:.1f}GB ({ram.percent}%)\n"
            f"Disk: {disk.used / 1e9:.0f}GB / {disk.total / 1e9:.0f}GB ({disk.percent}%)"
        )
    except Exception as e:
        return f"Could not get system info: {e}"


# Tool registry
JARVIS_TOOLS = [
    get_current_datetime,
    get_weather,
    web_search,
    scrape_url,
    remember_fact,
    recall_fact,
    search_memory,
    calculate,
    get_system_info,
]
