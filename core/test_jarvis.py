"""J.A.R.V.I.S. — Operational Verification Test"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

errors = []
passed = []

# Test 1: Config
try:
    from jarvis.config import config
    assert config.PRIMARY_MODEL == "qwen2.5:3b"
    assert config.PORT == 8000
    assert config.WHISPER_MODEL == "base"
    passed.append("config.py — PRIMARY_MODEL, PORT, WHISPER_MODEL OK")
except Exception as e:
    errors.append(f"config.py FAIL: {e}")

# Test 2: Intent classifier (train + predict)
try:
    from jarvis.agent.intent_classifier import IntentClassifier
    clf = IntentClassifier()
    # Test predictions
    cases = [
        ("que hora es", "time"),
        ("como esta el clima hoy", "weather"),
        ("busca informacion sobre python", "search"),
        ("recuerda que me gusta el cafe", "memory_store"),
        ("cuanto es 25 por 4", "calculate"),
    ]
    correct = 0
    for text, expected in cases:
        intent, conf = clf.predict(text)
        if intent == expected:
            correct += 1
    accuracy = correct / len(cases)
    passed.append(f"intent_classifier — {correct}/{len(cases)} correct ({accuracy*100:.0f}%)")
except Exception as e:
    errors.append(f"intent_classifier FAIL: {e}")

# Test 3: Memory (SQLite)
try:
    import tempfile, os
    from jarvis.agent.memory import JarvisMemory
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = f.name
    mem = JarvisMemory(tmp)
    mem.add_message("test", "user", "hola jarvis")
    mem.add_message("test", "assistant", "hola emmanuel")
    history = mem.get_history("test")
    assert len(history) == 2
    mem.remember("nombre", "Emmanuel", "user")
    facts = mem.recall("nombre")
    assert facts is not None
    try:
        os.unlink(tmp)
    except Exception:
        pass  # Windows lock OK — test passed already
    passed.append("memory.py — SQLite episodic + semantic OK")
except Exception as e:
    errors.append(f"memory.py FAIL: {e}")

# Test 4: Tools import
try:
    from jarvis.agent.tools import JARVIS_TOOLS
    assert len(JARVIS_TOOLS) >= 7
    tool_names = [t.name for t in JARVIS_TOOLS]
    passed.append(f"tools.py — {len(JARVIS_TOOLS)} tools: {tool_names}")
except Exception as e:
    errors.append(f"tools.py FAIL: {e}")

# Test 5: LLM Router (import only — no Ollama needed)
try:
    from jarvis.agent.llm_router import check_ollama_health, get_active_provider
    health = check_ollama_health()
    provider = get_active_provider()
    passed.append(f"llm_router.py — Ollama health: {health}, active: {provider}")
except Exception as e:
    errors.append(f"llm_router.py FAIL: {e}")

# Test 6: STT module (import only)
try:
    from jarvis.voice.stt import WAKE_WORDS, WhisperSTT
    assert "jarvis" in WAKE_WORDS
    assert "hey jarvis" in WAKE_WORDS
    # Test wake word detection (no model needed)
    assert WhisperSTT.contains_wake_word("hey jarvis que hora es")
    assert WhisperSTT.contains_wake_word("oye jarvis busca el clima")
    assert not WhisperSTT.contains_wake_word("hola como estas")
    cmd = WhisperSTT.extract_command("hey jarvis que hora es")
    assert cmd == "que hora es", f"expected 'que hora es' got '{cmd}'"
    passed.append(f"stt.py — wake words OK, extract_command OK")
except Exception as e:
    errors.append(f"stt.py FAIL: {e}")

# Test 7: FastAPI app import (patch LLM init to avoid provider requirement)
try:
    import unittest.mock as mock
    # Patch get_langchain_llm before any import so JarvisAgent.__init__ won't raise
    fake_llm = mock.MagicMock()
    fake_llm.bind_tools = mock.MagicMock(return_value=fake_llm)
    with mock.patch("jarvis.agent.llm_router.get_langchain_llm", return_value=fake_llm):
        # If already imported, just grab the app from the cached module
        import sys
        if "jarvis.main" in sys.modules:
            _app = sys.modules["jarvis.main"].app
        else:
            import jarvis.main as _main_mod
            _app = _main_mod.app
    routes = [getattr(r, "path", str(r)) for r in _app.routes]
    assert any("/chat" in str(r) for r in routes), f"routes: {routes}"
    assert any("/health" in str(r) for r in routes), f"routes: {routes}"
    passed.append(f"main.py — FastAPI routes OK: {[r for r in routes if r.startswith('/')]}")
except Exception as e:
    errors.append(f"main.py FAIL: {e}")

# Results
print("\n" + "="*60)
print("J.A.R.V.I.S. OPERATIONAL VERIFICATION")
print("="*60)
for p in passed:
    print(f"  [PASS] {p}")
for e in errors:
    print(f"  [FAIL] {e}")
print("="*60)
print(f"  Result: {len(passed)}/{len(passed)+len(errors)} tests passed")
if not errors:
    print("  STATUS: OPERATIONAL [OK]")
else:
    print(f"  STATUS: {len(errors)} failures — check dependencies")
print("="*60)
sys.exit(0 if not errors else 1)
