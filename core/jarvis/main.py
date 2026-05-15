"""J.A.R.V.I.S. — FastAPI Application"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis.config import config
from jarvis.agent.core import jarvis
from jarvis.agent.intent_classifier import classifier
from jarvis.agent.memory import JarvisMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="J.A.R.V.I.S. API",
    description="Just A Rather Very Intelligent System — Multi-LLM AI Ecosystem",
    version="1.0.0",
)

# Serve static UI
UI_DIR = Path(__file__).parent / "ui"
if UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

memory = JarvisMemory(config.DB_PATH)


# --- Schemas ---

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    speak: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    provider: Optional[str] = None


class MemoryItem(BaseModel):
    key: str
    value: str
    category: str = "general"


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve Jarvis HUD UI."""
    index = UI_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>J.A.R.V.I.S. API</h1><p>Visit <a href='/docs'>/docs</a></p>")


@app.get("/health")
async def health():
    """System health check."""
    from jarvis.agent.llm_router import check_ollama_health, get_active_provider
    provider = get_active_provider()
    stats = memory.get_stats()
    return {
        "status": "online",
        "jarvis": config.JARVIS_NAME,
        "provider": provider,
        "ollama": check_ollama_health(),
        "memory": stats,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Chat with J.A.R.V.I.S."""
    # Classify intent (ML component demo)
    intent, confidence = classifier.predict(req.message)

    # Get response from agent
    response = await jarvis.chat(req.message, req.session_id)

    # TTS if requested
    if req.speak:
        from jarvis.voice.tts import tts
        tts.speak_async(response)

    return ChatResponse(
        response=response,
        session_id=req.session_id,
        intent=intent,
        intent_confidence=round(confidence, 4),
        provider=jarvis.get_provider().get("provider"),
    )


@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket streaming chat."""
    await websocket.accept()
    logger.info(f"[WS] Client connected: {session_id}")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")

            if not message.strip():
                continue

            # Stream response
            full = ""
            async for chunk in jarvis.chat_stream(message, session_id):
                full += chunk
                await websocket.send_json({"type": "chunk", "chunk": chunk})

            await websocket.send_json({"type": "done", "full": full})

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        await websocket.close()


@app.post("/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio to text."""
    try:
        from jarvis.voice.stt import stt
        audio_bytes = await file.read()
        text = stt.transcribe_audio(audio_bytes)
        is_wake = stt.contains_wake_word(text)
        command = stt.extract_command(text) if is_wake else text
        return {
            "transcript": text,
            "is_wake_word": is_wake,
            "command": command,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory")
async def get_memories():
    """List all long-term memories."""
    return {"memories": memory.get_all_memories()}


@app.post("/memory")
async def add_memory(item: MemoryItem):
    """Add a memory."""
    memory.remember(item.key, item.value, item.category)
    return {"status": "ok", "key": item.key}


@app.delete("/memory/{key}")
async def delete_memory(key: str):
    """Delete a memory by key."""
    memory.forget(key)
    return {"status": "ok", "key": key}


@app.get("/intent/classify")
async def classify_intent(text: str):
    """Classify the intent of a text (ML demo endpoint)."""
    intent, confidence = classifier.predict(text)
    top_k = classifier.predict_top_k(text, k=3)
    return {
        "text": text,
        "intent": intent,
        "confidence": round(confidence, 4),
        "top_k": top_k,
    }


@app.get("/provider")
async def get_provider():
    """Get info about the active LLM provider."""
    return jarvis.get_provider()


@app.get("/personas")
async def list_personas():
    """List all available personas."""
    return {"personas": jarvis.list_personas()}


@app.get("/persona")
async def get_persona():
    """Get current active persona."""
    return jarvis.get_current_persona()


@app.post("/persona/{name}")
async def set_persona(name: str):
    """Switch active persona."""
    result = jarvis.set_persona(name)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.get("/rebuild")
async def rebuild_agent():
    """Force LLM provider re-detection (e.g., after Ollama restart)."""
    info = jarvis.rebuild()
    return {"status": "rebuilt", "provider": info}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session."""
    return {"session_id": session_id, "history": jarvis.get_history(session_id)}


@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear conversation history for a session."""
    jarvis.clear_session(session_id)
    return {"status": "ok", "session_id": session_id}
