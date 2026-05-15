// J.A.R.V.I.S. — Frontend v2 · HUD Control System

const API = "http://localhost:8000";
const SESSION_ID = "emm_" + Math.random().toString(36).slice(2, 8);

let ws = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let msgCount = 0;
let streamingEl = null;

// ─── DOM refs ────────────────────────────────────────────────────────────────
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");
const btnMic = document.getElementById("btn-mic");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const providerInfo = document.getElementById("provider-info");
const costInfo = document.getElementById("cost-info");
const intentBadge = document.getElementById("intent-badge");
const typingInd = document.getElementById("typing-indicator");
const intentDisplay = document.getElementById("intent-display");
const confidenceBar = document.getElementById("confidence-bar");
const confidenceLabel = document.getElementById("confidence-label");
const sessionSpan = document.getElementById("sys-session");
const msgCountSpan = document.getElementById("msg-count");
const memCountSpan = document.getElementById("mem-count");
const footerProvider = document.getElementById("footer-provider");
const footerStatus = document.getElementById("footer-status");

// ─── Boot sequence ────────────────────────────────────────────────────────────
const BOOT_LINES = [
  "Iniciando núcleo J.A.R.V.I.S. v2.0...",
  "Cargando modelos de intención (TF-IDF + SVM)...",
  "Verificando proveedores LLM...",
  "Conectando memoria SQLite...",
  "Inicializando RAG ChromaDB...",
  "Enlazando WebSocket ws://localhost:8000...",
  "Calibrando personas: jarvis · coder · researcher · creative · planner",
  "Todos los sistemas operacionales. Bienvenido, Emmanuel.",
];

async function runBoot() {
  const overlay = document.getElementById("boot-overlay");
  const lines = document.getElementById("boot-lines");
  const bar = document.getElementById("boot-bar");
  const pct = document.getElementById("boot-pct");

  for (let i = 0; i < BOOT_LINES.length; i++) {
    await sleep(180 + Math.random() * 120);
    const d = document.createElement("div");
    d.textContent = "> " + BOOT_LINES[i];
    lines.appendChild(d);
    lines.scrollTop = lines.scrollHeight;
    const p = Math.round(((i + 1) / BOOT_LINES.length) * 100);
    bar.style.width = p + "%";
    pct.textContent = p + "%";
  }

  await sleep(400);
  overlay.classList.add("hidden");
  setTimeout(() => overlay.remove(), 900);
}

// ─── Clock ───────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  const days = ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"];
  const months = [
    "ENE",
    "FEB",
    "MAR",
    "ABR",
    "MAY",
    "JUN",
    "JUL",
    "AGO",
    "SEP",
    "OCT",
    "NOV",
    "DIC",
  ];
  document.getElementById("hud-time").textContent = `${hh}:${mm}:${ss}`;
  document.getElementById("hud-date").textContent =
    `${days[now.getDay()]} ${String(now.getDate()).padStart(2, "0")} ${months[now.getMonth()]} ${now.getFullYear()}`;
}

// ─── Hex grid background ──────────────────────────────────────────────────────
function initHexGrid() {
  const canvas = document.getElementById("bg-canvas");
  const ctx = canvas.getContext("2d");
  let W, H;

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
    draw();
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const size = 32,
      w = size * 2,
      h = Math.sqrt(3) * size;
    ctx.strokeStyle = "rgba(0,212,255,0.04)";
    ctx.lineWidth = 1;
    for (let row = -1; row < H / h + 1; row++) {
      for (let col = -1; col < W / w + 1; col++) {
        const x = col * w * 0.75;
        const y = row * h + (col % 2 === 0 ? 0 : h / 2);
        hexPath(ctx, x, y, size);
        ctx.stroke();
      }
    }
  }

  function hexPath(ctx, x, y, r) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i - Math.PI / 6;
      if (i === 0) ctx.moveTo(x + r * Math.cos(a), y + r * Math.sin(a));
      else ctx.lineTo(x + r * Math.cos(a), y + r * Math.sin(a));
    }
    ctx.closePath();
  }

  window.addEventListener("resize", resize);
  resize();
}

// ─── Particle system ──────────────────────────────────────────────────────────
function initParticles() {
  const canvas = document.getElementById("particle-canvas");
  const ctx = canvas.getContext("2d");
  let W,
    H,
    particles = [];

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function spawnParticle() {
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.3,
      vy: -Math.random() * 0.5 - 0.1,
      life: 1,
      decay: 0.003 + Math.random() * 0.004,
      r: Math.random() * 1.5 + 0.5,
    };
  }

  function tick() {
    ctx.clearRect(0, 0, W, H);
    while (particles.length < 40) particles.push(spawnParticle());

    particles.forEach((p, i) => {
      p.x += p.vx;
      p.y += p.vy;
      p.life -= p.decay;

      if (p.life <= 0 || p.y < -10) {
        particles[i] = spawnParticle();
        return;
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,212,255,${p.life * 0.4})`;
      ctx.fill();
    });

    requestAnimationFrame(tick);
  }

  window.addEventListener("resize", resize);
  resize();
  tick();
}

// ─── System stats (fake-animated, real if API provides) ───────────────────────
function animateSysStats() {
  function randPct(base, jitter) {
    return Math.min(99, Math.max(5, base + (Math.random() - 0.5) * jitter));
  }
  function update() {
    const cpu = randPct(45, 30);
    const ram = randPct(60, 15);
    document.getElementById("cpu-bar").style.width = cpu + "%";
    document.getElementById("ram-bar").style.width = ram + "%";
    document.getElementById("sys-cpu").textContent = cpu.toFixed(0) + "%";
    document.getElementById("sys-ram").textContent = ram.toFixed(0) + "%";
  }
  update();
  setInterval(update, 3000);
}

// ─── WebSocket ────────────────────────────────────────────────────────────────
function connectWebSocket() {
  const url = API.replace("http", "ws") + "/ws/" + SESSION_ID;
  ws = new WebSocket(url);

  ws.onopen = () => {
    setStatus("online", "ONLINE");
    footerStatus.textContent = "ONLINE";
  };

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.type === "chunk") appendStreamChunk(msg.chunk);
    else if (msg.type === "done") finalizeStream();
  };

  ws.onerror = () => setStatus("error", "ERROR");

  ws.onclose = () => {
    setStatus("", "RECONECTANDO");
    footerStatus.textContent = "RECONNECTING";
    setTimeout(connectWebSocket, 3000);
  };
}

// ─── Messaging ───────────────────────────────────────────────────────────────
function sendMessage(text) {
  if (!text.trim()) return;
  appendMessage("user", text);
  chatInput.value = "";
  showTyping(true);
  classifyIntent(text);

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message: text }));
  } else {
    fetch(API + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: SESSION_ID }),
    })
      .then((r) => r.json())
      .then((data) => {
        showTyping(false);
        appendMessage("jarvis", data.response);
        updateIntent(data.intent, data.intent_confidence);
      })
      .catch(() => {
        showTyping(false);
        appendMessage(
          "jarvis",
          "Error de conexión. Verifique que el servidor J.A.R.V.I.S. esté corriendo en puerto 8000.",
        );
      });
  }
}

function appendMessage(role, text) {
  showTyping(false);
  msgCount++;
  msgCountSpan.textContent = msgCount;

  const wrap = document.createElement("div");
  wrap.className = "message " + (role === "jarvis" ? "jarvis-msg" : "user-msg");

  const avatar = document.createElement("div");
  avatar.className =
    "msg-avatar " + (role === "jarvis" ? "jarvis-avatar" : "user-avatar");
  avatar.textContent = role === "jarvis" ? "J" : "E";

  const body = document.createElement("div");
  body.className = "msg-body";

  const meta = document.createElement("div");
  meta.className = "msg-meta";
  const now = new Date();
  const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  meta.innerHTML =
    (role === "jarvis" ? "JARVIS" : "EMMANUEL") +
    `<span class="msg-time">${ts}</span>`;

  const content = document.createElement("div");
  content.className = "msg-text";
  content.textContent = text;

  body.appendChild(meta);
  body.appendChild(content);
  wrap.appendChild(avatar);
  wrap.appendChild(body);
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

function appendStreamChunk(chunk) {
  showTyping(false);
  if (!streamingEl) {
    msgCount++;
    msgCountSpan.textContent = msgCount;

    streamingEl = document.createElement("div");
    streamingEl.className = "message jarvis-msg";

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar jarvis-avatar";
    avatar.textContent = "J";

    const body = document.createElement("div");
    body.className = "msg-body";

    const meta = document.createElement("div");
    meta.className = "msg-meta";
    const now = new Date();
    const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    meta.innerHTML = `JARVIS <span class="msg-time">${ts}</span>`;

    const content = document.createElement("div");
    content.className = "msg-text";
    content.id = "streaming-content";

    const cursor = document.createElement("span");
    cursor.className = "cursor-blink";

    body.appendChild(meta);
    body.appendChild(content);
    body.appendChild(cursor);
    streamingEl.appendChild(avatar);
    streamingEl.appendChild(body);
    chatMessages.appendChild(streamingEl);
  }

  document.getElementById("streaming-content").textContent += chunk;
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function finalizeStream() {
  if (streamingEl) {
    const cursor = streamingEl.querySelector(".cursor-blink");
    if (cursor) cursor.remove();
    streamingEl = null;
  }
  showTyping(false);
}

// ─── UI helpers ───────────────────────────────────────────────────────────────
function setStatus(type, text) {
  statusDot.className = "status-dot " + type;
  statusText.textContent = text;
}

function showTyping(show) {
  typingInd.classList.toggle("hidden", !show);
}

// ─── Health + provider ────────────────────────────────────────────────────────
async function fetchHealth() {
  try {
    const r = await fetch(API + "/health", {
      signal: AbortSignal.timeout(5000),
    });
    const data = await r.json();
    const p = data.provider || {};

    const name = (p.provider || "---").toUpperCase();
    const model = p.model || "---";
    const cost = p.cost || "---";
    const local = p.local ? "LOCAL" : "CLOUD";

    providerInfo.textContent = `LLM: ${name} [${model}]`;
    costInfo.textContent = `COST: ${cost.toUpperCase()} · ${local}`;
    footerProvider.textContent = `LLM: ${name}`;

    if (data.status === "online") setStatus("online", "ONLINE");

    // Update provider list panel
    updateProviderPanel(p.provider, data.ollama);

    // Memory stats
    if (data.memory) {
      memCountSpan.textContent = data.memory.total_memories ?? "---";
    }
  } catch {
    providerInfo.textContent = "LLM: OFFLINE";
    setStatus("error", "OFFLINE");
  }
}

function updateProviderPanel(activeProvider, ollamaOk) {
  const items = {
    ollama: document.getElementById("prov-ollama"),
    groq: document.getElementById("prov-groq"),
    anthropic: document.getElementById("prov-anthropic"),
    openai: document.getElementById("prov-openai"),
  };

  Object.keys(items).forEach((key) => {
    const el = items[key];
    const dot = el.querySelector(".prov-dot");
    const status = el.querySelector(".prov-status");
    el.className = "provider-item";

    if (key === activeProvider) {
      el.classList.add("active");
      status.textContent = "ACTIVO";
      dot.style.background = "var(--green)";
      dot.style.boxShadow = "0 0 6px var(--green)";
    } else if (key === "ollama") {
      status.textContent = ollamaOk ? "online" : "offline";
      dot.style.background = ollamaOk ? "var(--green)" : "var(--text-dim)";
      dot.style.boxShadow = ollamaOk ? "0 0 6px var(--green)" : "none";
    } else {
      el.classList.add("standby");
      status.textContent = "standby";
      dot.style.background = "var(--orange)";
      dot.style.boxShadow = "none";
    }
  });
}

// ─── Intent classification ────────────────────────────────────────────────────
async function classifyIntent(text) {
  try {
    const r = await fetch(
      API + "/intent/classify?text=" + encodeURIComponent(text),
    );
    const data = await r.json();
    updateIntent(data.intent, data.confidence);
  } catch {
    /* silent */
  }
}

function updateIntent(intent, confidence) {
  if (!intent) return;
  const label = intent.toUpperCase().replace(/_/g, " ");
  intentDisplay.textContent = label;

  const pct = Math.round((confidence || 0) * 100);
  confidenceBar.style.width = pct + "%";
  confidenceLabel.textContent = pct + "%";

  intentBadge.textContent = "► " + label;
  intentBadge.classList.add("visible");
  setTimeout(() => intentBadge.classList.remove("visible"), 4000);
}

// ─── Memory ──────────────────────────────────────────────────────────────────
async function loadMemories() {
  try {
    const r = await fetch(API + "/memory");
    const data = await r.json();
    const list = document.getElementById("memory-list");
    list.innerHTML = "";

    if (!data.memories.length) {
      list.innerHTML =
        '<div class="memory-entry">Sin memorias almacenadas.</div>';
      return;
    }
    data.memories.slice(0, 10).forEach((m) => {
      const el = document.createElement("div");
      el.className = "memory-entry";
      el.innerHTML = `<strong>${m.key}</strong>: ${m.value}`;
      list.appendChild(el);
    });
    memCountSpan.textContent = data.memories.length;
  } catch {
    /* silent */
  }
}

// ─── Persona switcher ─────────────────────────────────────────────────────────
async function setPersona(name) {
  try {
    const r = await fetch(API + "/persona/" + name, { method: "POST" });
    if (r.ok) {
      document.querySelectorAll(".persona-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.persona === name);
      });
      appendMessage("jarvis", `Modo ${name.toUpperCase()} activado.`);
    }
  } catch {
    appendMessage("jarvis", "No se pudo cambiar la persona. Servidor offline.");
  }
}

// ─── Session controls ─────────────────────────────────────────────────────────
async function clearSession() {
  try {
    await fetch(API + "/history/" + SESSION_ID, { method: "DELETE" });
  } catch {
    /* silent */
  }
  chatMessages.innerHTML = "";
  msgCount = 0;
  msgCountSpan.textContent = 0;
  appendMessage("jarvis", "Sesión limpiada. ¿En qué puedo ayudarle?");
}

async function rebuildAgent() {
  try {
    const r = await fetch(API + "/rebuild");
    const data = await r.json();
    appendMessage(
      "jarvis",
      `LLM reconectado: ${data.provider?.provider || "---"}`,
    );
    await fetchHealth();
  } catch {
    appendMessage("jarvis", "Error al reconectar el LLM.");
  }
}

// ─── Voice ───────────────────────────────────────────────────────────────────
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = sendAudio;
    mediaRecorder.start();
    isRecording = true;
    btnMic.classList.add("active");
  } catch {
    appendMessage(
      "jarvis",
      "Acceso al micrófono denegado. Active en configuración del navegador.",
    );
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    isRecording = false;
    btnMic.classList.remove("active");
  }
}

async function sendAudio() {
  if (!audioChunks.length) return;
  const blob = new Blob(audioChunks, { type: "audio/webm" });
  const formData = new FormData();
  formData.append("file", blob, "voice.webm");
  try {
    const r = await fetch(API + "/voice/transcribe", {
      method: "POST",
      body: formData,
    });
    const data = await r.json();
    if (data.command) {
      chatInput.value = data.command;
      sendMessage(data.command);
    }
  } catch {
    /* silent */
  }
}

// ─── Utils ───────────────────────────────────────────────────────────────────
function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // Set greeting time
  const greetTime = document.getElementById("greet-time");
  if (greetTime) {
    const now = new Date();
    greetTime.textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  }

  sessionSpan.textContent = SESSION_ID;

  // Background layers
  initHexGrid();
  initParticles();
  animateSysStats();

  // Clock
  updateClock();
  setInterval(updateClock, 1000);

  // Boot sequence
  await runBoot();

  // Connect
  connectWebSocket();
  await fetchHealth();
  setInterval(fetchHealth, 30000);
});

// ─── Events ───────────────────────────────────────────────────────────────────
btnSend.addEventListener("click", () => sendMessage(chatInput.value));

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(chatInput.value);
  }
});

btnMic.addEventListener("mousedown", startRecording);
btnMic.addEventListener("mouseup", stopRecording);
btnMic.addEventListener("touchstart", (e) => {
  e.preventDefault();
  startRecording();
});
btnMic.addEventListener("touchend", (e) => {
  e.preventDefault();
  stopRecording();
});
