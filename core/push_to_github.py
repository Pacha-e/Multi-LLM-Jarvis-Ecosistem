#!/usr/bin/env python3
"""
J.A.R.V.I.S. — GitHub Push Script
Pushes all project files to Pacha-e/Multi-LLM-Jarvis-Ecosistem via GitHub API.

Usage:
    python push_to_github.py <YOUR_GITHUB_TOKEN>

Or set env var:
    GITHUB_TOKEN=xxx python push_to_github.py
"""

import sys
import os
import base64
import json
import pathlib
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
OWNER = "Pacha-e"
REPO = "Multi-LLM-Jarvis-Ecosistem"
BRANCH = "main"
BASE_DIR = pathlib.Path(__file__).parent.resolve()

TOKEN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    print("[!] Provide GitHub token: python push_to_github.py <TOKEN>")
    sys.exit(1)

# ── Files to upload ───────────────────────────────────────────────────────────
# (relative path inside repo, local path)
FILES = [
    ("README.md", "README.md"),
    ("requirements.txt", "requirements.txt"),
    ("env.example", "env.example"),
    ("run.py", "run.py"),
    ("Dockerfile", "Dockerfile"),
    ("docker-compose.yml", "docker-compose.yml"),
    ("LICENSE", "LICENSE"),
    ("gitignore.txt", "gitignore.txt"),
    # jarvis package
    ("jarvis/__init__.py", "jarvis/__init__.py"),
    ("jarvis/config.py", "jarvis/config.py"),
    ("jarvis/main.py", "jarvis/main.py"),
    # agent subpackage
    ("jarvis/agent/__init__.py", "jarvis/agent/__init__.py"),
    ("jarvis/agent/memory.py", "jarvis/agent/memory.py"),
    ("jarvis/agent/llm_router.py", "jarvis/agent/llm_router.py"),
    ("jarvis/agent/tools.py", "jarvis/agent/tools.py"),
    ("jarvis/agent/intent_classifier.py", "jarvis/agent/intent_classifier.py"),
    ("jarvis/agent/core.py", "jarvis/agent/core.py"),
    # voice subpackage
    ("jarvis/voice/__init__.py", "jarvis/voice/__init__.py"),
    ("jarvis/voice/stt.py", "jarvis/voice/stt.py"),
    ("jarvis/voice/tts.py", "jarvis/voice/tts.py"),
    # UI
    ("jarvis/ui/index.html", "jarvis/ui/index.html"),
    ("jarvis/ui/style.css", "jarvis/ui/style.css"),
    ("jarvis/ui/app.js", "jarvis/ui/app.js"),
    # scripts
    ("scripts/setup_wsl.sh", "scripts/setup_wsl.sh"),
    ("scripts/start.sh", "scripts/start.sh"),
    # docs
    ("docs/informe_proyecto.md", "docs/informe_proyecto.md"),
]

# ── GitHub API helpers ────────────────────────────────────────────────────────
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
    "User-Agent": "jarvis-push-script",
}


def gh_request(method, url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return json.loads(body) if body else {}, e.code


def get_sha(path):
    """Get existing file SHA (needed for updates)."""
    result, status = gh_request("GET", f"{API}/{path}?ref={BRANCH}")
    if status == 200:
        return result.get("sha")
    return None


def upload_file(repo_path, local_path):
    """Create or update a file in the repo."""
    full_local = BASE_DIR / local_path
    if not full_local.exists():
        print(f"  [SKIP] Not found locally: {local_path}")
        return False

    content = full_local.read_bytes()
    encoded = base64.b64encode(content).decode()

    sha = get_sha(repo_path)
    payload = {
        "message": f"feat: add {repo_path}",
        "content": encoded,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
        verb = "UPDATE"
    else:
        verb = "CREATE"

    result, status = gh_request("PUT", f"{API}/{repo_path}", payload)
    if status in (200, 201):
        print(f"  [OK] {verb}: {repo_path}")
        return True
    else:
        print(f"  [ERR] {repo_path} — HTTP {status}: {result.get('message','')}")
        return False


# ── README content ────────────────────────────────────────────────────────────
README = """# J.A.R.V.I.S. — Multi-LLM AI Ecosystem

> **Just A Rather Very Intelligent System**
> Proyecto Final — Introducción a la Inteligencia Artificial 2026-1
> Universidad EAFIT | Emmanuel Hernández

## Descripción

Asistente de IA multimodal (voz + texto) que integra NLP, ML clásico, redes neuronales y agentes inteligentes.
Optimizado para GTX 1650 (4GB VRAM), operación 24/7 en WSL2.

## Conceptos IA Aplicados

| Concepto | Implementación |
|---------|----------------|
| NLP / ASR | Faster-Whisper (encoder-decoder Transformer) |
| ML Clásico | TF-IDF + SVM clasificador de intenciones (93% accuracy) |
| Redes Neuronales | LLMs vía Transformers: Qwen2.5, Llama-3.1, Claude |
| Agentes Inteligentes | LangGraph ReAct: Reason → Act → Observe |

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    J.A.R.V.I.S.                     │
├──────────────┬──────────────────┬───────────────────┤
│   Voz (STT)  │   Intent (ML)    │   UI (FastAPI)    │
│  Whisper/GPU │  TF-IDF + SVM    │  WebSocket + HUD  │
├──────────────┴──────────────────┴───────────────────┤
│              LangGraph ReAct Agent                   │
│   Memory (SQLite) + Tools + LLM Router               │
├─────────────────────────────────────────────────────┤
│  Ollama → Groq → Anthropic → OpenAI (prioridad)     │
└─────────────────────────────────────────────────────┘
```

## Instalación Rápida (WSL2)

```bash
git clone https://github.com/Pacha-e/Multi-LLM-Jarvis-Ecosistem.git
cd Multi-LLM-Jarvis-Ecosistem

# Setup completo (Ollama + systemd + Python venv + modelo)
bash scripts/setup_wsl.sh

# O inicio manual
bash scripts/start.sh
```

UI disponible en `http://localhost:8000`

## Configuración

```bash
cp env.example jarvis.env
# Editar jarvis.env con API keys
```

- `GROQ_API_KEY` — gratis (30K tokens/min) en console.groq.com
- `PRIMARY_MODEL` — modelo Ollama (default: qwen2.5:3b)
- `WHISPER_MODEL` — tamaño Whisper (default: base)

## Resultados

### Clasificador TF-IDF + SVM
| Métrica | Valor |
|---------|-------|
| Accuracy global | **93%** |
| Macro F1 | **0.96** |
| Inferencia | <5ms (CPU) |
| Clases | 8 intenciones |

### Tiempos de Respuesta
| Componente | Tiempo |
|-----------|--------|
| STT Whisper base (GPU) | ~300ms |
| Intent classification | <5ms |
| LLM Ollama qwen2.5:3b | 500-2000ms |
| TTS pyttsx3 | <100ms |
| **Total ciclo voz** | **~1-3s** |

## Estructura del Proyecto

```
├── jarvis/
│   ├── config.py          # Configuración centralizada
│   ├── main.py            # FastAPI app + WebSocket
│   ├── agent/
│   │   ├── core.py        # LangGraph ReAct Agent
│   │   ├── llm_router.py  # Multi-LLM fallback router
│   │   ├── tools.py       # 8 LangChain tools
│   │   ├── memory.py      # SQLite episódica + semántica
│   │   └── intent_classifier.py  # TF-IDF + SVM
│   ├── voice/
│   │   ├── stt.py         # Faster-Whisper STT
│   │   └── tts.py         # pyttsx3 + gTTS
│   └── ui/                # Cyberpunk HUD (HTML/CSS/JS)
├── scripts/
│   ├── setup_wsl.sh       # Setup WSL2 + systemd
│   └── start.sh           # Quick start
├── docs/
│   └── informe_proyecto.md
├── run.py                 # Entry point
├── requirements.txt
└── env.example
```

## Docker

```bash
docker compose up -d
```

## Referencias

1. Vaswani et al. (2017). *Attention Is All You Need.* NeurIPS.
2. Radford et al. (2022). *Robust Speech Recognition via Large-Scale Weak Supervision.* OpenAI.
3. Yao et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR.
4. Yang et al. (2024). *Qwen2.5 Technical Report.* Alibaba Cloud.
5. LangChain (2024). *LangGraph.* https://langchain-ai.github.io/langgraph/

---

*Emmanuel Hernández — Ingeniería de Sistemas — EAFIT 2026-1*
"""


def create_readme():
    """Create README with full content."""
    encoded = base64.b64encode(README.encode()).decode()
    sha = get_sha("README.md")
    payload = {
        "message": "feat: add README — J.A.R.V.I.S. Multi-LLM AI Ecosystem",
        "content": encoded,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    result, status = gh_request("PUT", f"{API}/README.md", payload)
    if status in (200, 201):
        print("  [OK] CREATE: README.md")
        return True
    print(f"  [ERR] README — HTTP {status}: {result.get('message','')}")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n[+] Pushing J.A.R.V.I.S. to github.com/{OWNER}/{REPO}\n")

    ok = 0
    fail = 0

    # README first (initializes repo if empty)
    print("[README]")
    if create_readme():
        ok += 1
    else:
        fail += 1

    # All other files
    for repo_path, local_path in FILES:
        if repo_path == "README.md":
            continue  # Already done
        if upload_file(repo_path, local_path):
            ok += 1
        else:
            fail += 1

    print(f"\n[+] Done: {ok} uploaded, {fail} failed")
    print(f"[+] View: https://github.com/{OWNER}/{REPO}")


if __name__ == "__main__":
    main()
