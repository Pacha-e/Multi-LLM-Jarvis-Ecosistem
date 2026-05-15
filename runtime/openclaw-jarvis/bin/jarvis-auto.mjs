#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.JARVIS_HOME ? resolve(process.env.JARVIS_HOME) : resolve(SCRIPT_DIR, "..");
const DISPATCHER = join(ROOT, "bin", "jarvis-dispatch.mjs");
const RUNS_DIR = join(ROOT, "runs");
const CONFIG_DIR = join(ROOT, "config");
const CONFIG_FILE = join(CONFIG_DIR, "jarvis-profile.json");
const MAX_HANDOFF_CHARS = 2400;

const validRoles = new Set([
  "orion",
  "kiro",
  "nova",
  "spark",
  "iris",
  "kiro-cli",
  "claude",
  "claude-plan",
  "claude-architect",
  "claude-review",
  "codex",
  "codex-write",
  "codex-plan",
  "codex-implement",
  "codex-review",
  "gemini",
  "qwen",
  "aider",
  "multica"
]);

function defaultConfig() {
  return {
    version: 1,
    profileName: "Jarvis",
    ux: {
      defaultMode: "auto",
      compactOutput: true,
      showRunPath: true,
      beginnerFriendly: true,
      terminalUi: true,
      voiceGreeting: true,
      speakChatReplies: true
    },
    safety: {
      noAutoCommit: true,
      noAutoPush: true,
      noSecretsInLogs: true,
      preserveUserChanges: true
    },
    cost: {
      defaultBudget: "economy",
      orchestrationBackend: "subscription-cli",
      subscriptionCoordinator: "claude",
      preferSubscriptionCli: true,
      avoidApiByDefault: true,
      localFirstVoice: true,
      economyReviewOnlyWhenRisky: true,
      riskKeywords: [
        "auth",
        "login",
        "seguridad",
        "security",
        "pago",
        "payment",
        "stripe",
        "database",
        "base de datos",
        "migration",
        "migracion",
        "deploy",
        "produccion",
        "production",
        "secret",
        "token"
      ]
    },
    voice: {
      style: "cinematic-original",
      voiceName: "",
      preferredVoiceNames: [
        "Microsoft George",
        "Microsoft David Desktop",
        "Microsoft Hazel Desktop",
        "Microsoft Zira Desktop"
      ],
      rate: -1,
      volume: 100,
      sample: "Good evening. Jarvis is online. Systems are nominal."
    },
    selfImprovement: {
      defaultMode: "audit-first",
      applyRequiresFlag: true,
      target: ROOT
    }
  };
}

function readConfig() {
  const fallback = defaultConfig();
  if (!existsSync(CONFIG_FILE)) return fallback;
  try {
    return mergeConfig(fallback, JSON.parse(readFileSync(CONFIG_FILE, "utf8")));
  } catch {
    return fallback;
  }
}

function writeConfig(config) {
  mkdirSync(CONFIG_DIR, { recursive: true });
  writeFileSync(CONFIG_FILE, `${JSON.stringify(config, null, 2)}\n`);
}

function ensureConfig() {
  const config = readConfig();
  if (!existsSync(CONFIG_FILE)) writeConfig(config);
  return config;
}

function mergeConfig(base, override) {
  if (!override || typeof override !== "object") return base;
  const out = Array.isArray(base) ? [...base] : { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (value && typeof value === "object" && !Array.isArray(value) && base[key] && typeof base[key] === "object") {
      out[key] = mergeConfig(base[key], value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

function usage() {
  console.log(`Usage:
  jarvis [prompt...]
  jarvis setup
  jarvis doctor
  jarvis budget
  jarvis improve [--apply]
  jarvis voice list|set|test
  jarvis reels <url> [--lang es]
  jarvis --target <path> [--mode auto|fast|full|council] [--budget economy|balanced|max] [--backend subscription-cli|openclaw-agent] [--dry-run] [--speak] "prompt"
  jarvis chat [--target <path>]
  jarvis voz [--target <path>]
  jarvis --listen --speak [--target <path>]

Examples:
  jarvis "revisa este repo y dime que falta para dejarlo operativo"
  jarvis --target /home/emmanuel/proyecto "arregla el bug del login y revisa el cambio"
  jarvis --mode full "prepara, implementa y valida esta feature"
  jarvis --role qwen "dame una segunda opinion critica sobre esta arquitectura"
  jarvis improve
  jarvis improve --apply
  jarvis budget
  jarvis voice test
  jarvis voice list
  jarvis voice set --name "Microsoft David Desktop" --rate -1 --volume 100

Modes:
  auto     Clasifica la intencion y usa la ruta util minima.
  fast     Usa un solo especialista.
  full     Pipeline completo del backend activo.
  council  Claude/Codex/Qwen por defecto; Nova/Qwen/Iris con openclaw-agent.

Budgets:
  economy  Prefer subscription CLIs, local commands, and one specialist.
  balanced Use specialist + reviewer when useful.
  max      Use the full multi-agent pipeline.

Backends:
  subscription-cli  Distributed phases through Claude/Codex subscriptions.
  openclaw-agent    Distributed phases through OpenClaw local agents.
`);
}

function parseArgs(argv) {
  const args = {
    target: process.cwd(),
    mode: "auto",
    dryRun: false,
    speak: false,
    listen: false,
    chat: false,
    apply: false,
    command: null,
    voiceAction: null,
    voiceName: null,
    voiceRate: null,
    voiceVolume: null,
    voiceStyle: null,
    reelUrl: null,
    reelLang: null,
    promptParts: []
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") args.help = true;
    else if (["setup", "doctor", "budget", "improve", "voice", "start", "stop", "status", "reels"].includes(arg) && !args.command && args.promptParts.length === 0) {
      args.command = arg;
      if (arg === "voice" && argv[i + 1] && !argv[i + 1].startsWith("-")) args.voiceAction = argv[++i];
      if (arg === "reels" && argv[i + 1] && !argv[i + 1].startsWith("-")) args.reelUrl = argv[++i];
    }
    else if (arg === "--target" || arg === "-t") {
      args.target = argv[++i];
      args.targetProvided = true;
    }
    else if (arg === "--mode" || arg === "-m") args.mode = argv[++i];
    else if (arg === "--budget" || arg === "-b") args.budget = argv[++i];
    else if (arg === "--backend") args.backend = argv[++i];
    else if (arg === "--role" || arg === "-r") args.role = argv[++i];
    else if (arg === "--dry-run") args.dryRun = true;
    else if (arg === "--apply") args.apply = true;
    else if (arg === "--name") args.voiceName = argv[++i];
    else if (arg === "--rate") args.voiceRate = Number(argv[++i]);
    else if (arg === "--volume") args.voiceVolume = Number(argv[++i]);
    else if (arg === "--style") args.voiceStyle = argv[++i];
    else if (arg === "--lang") args.reelLang = argv[++i];
    else if (arg === "--speak") args.speak = true;
    else if (arg === "--listen" || arg === "--voice") args.listen = true;
    else if (arg === "--chat") args.chat = true;
    else if (arg === "--no-review") args.noReview = true;
    else if (arg === "chat" && args.promptParts.length === 0) args.chat = true;
    else if ((arg === "voz" || arg === "voice" || arg === "listen") && args.promptParts.length === 0) {
      args.listen = true;
      args.speak = true;
    } else {
      args.promptParts.push(arg);
    }
  }

  args.prompt = args.promptParts.join(" ").trim();
  args.target = resolve(args.target);
  return args;
}

function normalize(text) {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function containsAny(text, words) {
  return words.some((word) => text.includes(word));
}

function unique(items) {
  return [...new Set(items)];
}

function routePrompt(prompt, options) {
  if (options.role) {
    if (!validRoles.has(options.role)) throw new Error(`Rol invalido: ${options.role}`);
    return {
      mode: "manual-role",
      reason: `Rol forzado por usuario: ${options.role}`,
      roles: [options.role]
    };
  }

  const p = normalize(prompt);
  const config = readConfig();
  const budget = options.budget || config.cost?.defaultBudget || "economy";
  const backend = options.backend || config.cost?.orchestrationBackend || "subscription-cli";
  const risky = isRiskyPrompt(p, config);

  if (options.mode === "full") {
    return {
      mode: "full",
      reason: "Modo full solicitado.",
      roles: routeForBackend("full", backend, { budget, risky, noReview: options.noReview })
    };
  }

  if (options.mode === "council") {
    return {
      mode: "council",
      reason: "Modo council solicitado.",
      roles: backend === "openclaw-agent" ? ["nova", "qwen", "iris"] : ["claude-architect", "codex-review", "qwen"]
    };
  }

  if (budget === "max") {
    return {
      mode: "max",
      reason: backend === "openclaw-agent"
        ? "Presupuesto max: pipeline multi-agente completo via OpenClaw."
        : "Presupuesto max: pipeline distribuido completo via subscripciones Claude/Codex.",
      roles: routeForBackend("full", backend, { budget, risky, noReview: options.noReview })
    };
  }

  const directRole = detectDirectRole(p);
  if (directRole) {
    return {
      mode: "direct",
      reason: `El prompt pide usar ${directRole}.`,
      roles: [directRole]
    };
  }

  const wantsFull = containsAny(p, [
    "pipeline completo",
    "modo full",
    "full",
    "de punta a punta",
    "end to end",
    "100%",
    "dejalo operativo",
    "todo el proyecto",
    "maxima delegacion",
    "orquesta",
    "orquestador"
  ]);
  const wantsImplementation = containsAny(p, [
    "implementa",
    "arregla",
    "corrige",
    "soluciona",
    "modifica",
    "edita",
    "crea",
    "construye",
    "agrega",
    "refactor",
    "haz el cambio",
    "fix",
    "bug"
  ]);
  const wantsReview = containsAny(p, [
    "revisa",
    "review",
    "audita",
    "valida",
    "verifica",
    "comprueba",
    "segunda opinion",
    "critica",
    "seguridad",
    "vulnerabilidad"
  ]);
  const wantsArchitecture = containsAny(p, [
    "arquitectura",
    "disena",
    "diseña",
    "debug",
    "root cause",
    "causa raiz",
    "investiga",
    "diagnostica",
    "analiza el problema",
    "decision tecnica"
  ]);
  const wantsSpec = containsAny(p, [
    "spec",
    "especificacion",
    "criterios de aceptacion",
    "planifica",
    "plan",
    "divide",
    "tareas",
    "roadmap",
    "backlog"
  ]);
  const wantsAgentPlatform = containsAny(p, [
    "multica",
    "crear agente",
    "crea agente",
    "agent create"
  ]);
  const wantsSelfImprovement = containsAny(p, [
    "mejora tu setup",
    "mejorate",
    "mejorarte",
    "auto mejora",
    "automejora",
    "self improve",
    "evalua tu setup",
    "configurate",
    "configura tu setup"
  ]);

  if (wantsAgentPlatform) {
    return {
      mode: "platform",
      reason: "El prompt habla de Multica o creacion de agentes.",
      roles: ["multica"]
    };
  }

  if (wantsSelfImprovement) {
    return {
      mode: "self-improvement",
      reason: "La solicitud apunta a evaluar o mejorar el setup de Jarvis.",
      roles: routeForBackend("architecture", backend, { budget, risky: true, noReview: options.noReview })
    };
  }

  if (wantsFull) {
    return {
      mode: "full",
      reason: "La solicitud pide ejecucion amplia/de punta a punta.",
      roles: routeForBackend("full", backend, { budget, risky, noReview: options.noReview })
    };
  }

  if (options.mode === "fast") {
    return fastRoute({ wantsImplementation, wantsReview, wantsArchitecture, wantsSpec, backend });
  }

  if (wantsImplementation) {
    return {
      mode: "auto",
      reason: backend === "openclaw-agent"
        ? "Cambio de codigo distribuido via OpenClaw."
        : "Cambio de codigo distribuido via subscripciones: plan -> implementacion -> review.",
      roles: routeForBackend("implementation", backend, { budget, risky, noReview: options.noReview })
    };
  }

  if (wantsArchitecture) {
    return {
      mode: "auto",
      reason: backend === "openclaw-agent"
        ? "Arquitectura/debug distribuido via OpenClaw."
        : "Arquitectura/debug distribuido via Claude/Codex subscriptions.",
      roles: routeForBackend("architecture", backend, { budget, risky, noReview: options.noReview })
    };
  }

  if (wantsReview) {
    return {
      mode: "auto",
      reason: backend === "openclaw-agent"
        ? "Review/validacion via OpenClaw."
        : "Review/validacion distribuida via Codex/Claude subscriptions.",
      roles: routeForBackend("review", backend, { budget, risky, noReview: options.noReview })
    };
  }

  if (wantsSpec) {
    return {
      mode: "auto",
      reason: backend === "openclaw-agent"
        ? "Plan/spec via OpenClaw."
        : "Plan/spec distribuido via Claude/Codex subscriptions.",
      roles: routeForBackend("spec", backend, { budget, risky, noReview: options.noReview })
    };
  }

  return {
    mode: "auto",
    reason: backend === "openclaw-agent"
      ? "Consulta general: Orion decide la ruta via OpenClaw."
      : "Consulta general: Claude subscription coordina sin Gemini API.",
    roles: routeForBackend("general", backend, { budget, risky, noReview: options.noReview })
  };
}

function routeForBackend(kind, backend, { budget, risky, noReview }) {
  if (backend === "openclaw-agent") {
    if (kind === "full") return ["orion", "kiro", "nova", "spark", "iris"];
    if (kind === "implementation") return noReview ? ["spark"] : ["spark", "iris"];
    if (kind === "architecture") return noReview ? ["nova"] : ["nova", "iris"];
    if (kind === "review") return ["iris"];
    if (kind === "spec") return ["orion", "kiro"];
    return ["orion"];
  }

  if (kind === "full") return ["claude-plan", "codex-plan", "claude-architect", "codex-implement", "codex-review"];
  if (kind === "implementation") {
    if (noReview) return ["claude-plan", "codex-implement"];
    return budget === "max" || risky
      ? ["claude-plan", "codex-implement", "claude-review", "codex-review"]
      : ["claude-plan", "codex-implement", "codex-review"];
  }
  if (kind === "architecture") return noReview ? ["claude-architect"] : ["claude-architect", "codex-review"];
  if (kind === "review") return ["codex-review", "claude-review"];
  if (kind === "spec") return ["claude-plan", "codex-plan"];
  return ["claude-plan"];
}

function isRiskyPrompt(prompt, config) {
  return (config.cost?.riskKeywords || []).some((word) => prompt.includes(normalize(word)));
}

function detectDirectRole(prompt) {
  const direct = [
    ["codex", "codex"],
    ["claude", "claude"],
    ["qwen", "qwen"],
    ["gemini", "gemini"],
    ["aider", "aider"],
    ["kiro-cli", "kiro-cli"],
    ["multica", "multica"]
  ];
  for (const [needle, role] of direct) {
    if (prompt.includes(`usa ${needle}`) || prompt.includes(`con ${needle}`) || prompt.includes(`en ${needle}`)) {
      return role;
    }
  }
  return null;
}

function fastRoute(flags) {
  if (flags.backend !== "openclaw-agent") {
    if (flags.wantsImplementation) return { mode: "fast", reason: "Modo fast: Codex implementa directo.", roles: ["codex-implement"] };
    if (flags.wantsArchitecture) return { mode: "fast", reason: "Modo fast: Claude arquitectura directo.", roles: ["claude-architect"] };
    if (flags.wantsReview) return { mode: "fast", reason: "Modo fast: Codex review directo.", roles: ["codex-review"] };
    if (flags.wantsSpec) return { mode: "fast", reason: "Modo fast: Claude plan directo.", roles: ["claude-plan"] };
    return { mode: "fast", reason: "Modo fast: Claude consulta general.", roles: ["claude-plan"] };
  }
  if (flags.wantsImplementation) {
    return { mode: "fast", reason: "Modo fast: implementacion directa.", roles: ["spark"] };
  }
  if (flags.wantsArchitecture) {
    return { mode: "fast", reason: "Modo fast: analisis tecnico directo.", roles: ["nova"] };
  }
  if (flags.wantsReview) {
    return { mode: "fast", reason: "Modo fast: review directa.", roles: ["iris"] };
  }
  if (flags.wantsSpec) {
    return { mode: "fast", reason: "Modo fast: plan directo.", roles: ["orion"] };
  }
  return { mode: "fast", reason: "Modo fast: consulta general.", roles: ["orion"] };
}

function buildStepObjective({ prompt, route, role, stepIndex, stepCount, target, previousOutputs }) {
  const prior = previousOutputs.length === 0
    ? "none"
    : previousOutputs
      .map((item) => `${item.role} ${item.status}: ${trimForHandoff(item.output)}`)
      .join("\n\n");

  return [
    "User request:",
    prompt,
    "",
    `Route: ${route.roles.join(" -> ")}`,
    `Reason: ${route.reason}`,
    `Target: ${target}`,
    `Step: ${role} ${stepIndex + 1}/${stepCount}`,
    "",
    "Previous:",
    prior,
    "",
    "Rules: stay in role; avoid duplicate work; preserve unrelated changes; no secrets; if editing, make the smallest safe change and verify; if reviewing, give concrete severity+fix; return compact status/actions/evidence/files/risks/handoff."
  ].join("\n");
}

function runDispatch({ role, objective, target, dryRun }) {
  if (dryRun) {
    return {
      status: 0,
      signal: null,
      stdout: `${JSON.stringify({
        status: "dry_run",
        dispatcher: DISPATCHER,
        role,
        target,
        objectivePreview: objective.slice(0, 700)
      }, null, 2)}\n`,
      stderr: ""
    };
  }

  const args = [
    DISPATCHER,
    "--role",
    role,
    "--objective",
    objective,
    "--target",
    target
  ];
  return spawnSync(process.execPath, args, {
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024
  });
}

function fallbackRole(role) {
  return {
    "codex-write": "spark",
    "codex-implement": "spark",
    "codex-plan": "claude-plan",
    "codex-review": "qwen",
    claude: "nova",
    "claude-plan": "codex-plan",
    "claude-architect": "codex-plan",
    "claude-review": "codex-review",
    qwen: "iris"
  }[role] || "";
}

function trimForHandoff(text) {
  const clean = (text || "").trim();
  if (clean.length <= MAX_HANDOFF_CHARS) return clean;
  return `${clean.slice(0, 1200)}\n\n[...salida recortada...]\n\n${clean.slice(-4800)}`;
}

function ensureTrailingNewline(text) {
  return text.endsWith("\n") ? text : `${text}\n`;
}

function color(code, text) {
  if (!output.isTTY || process.env.NO_COLOR) return text;
  return `\x1b[${code}m${text}\x1b[0m`;
}

function uiRule(label = "") {
  const title = label ? ` ${label} ` : "";
  const width = Math.max(50, Math.min(88, output.columns || 72));
  const side = Math.max(0, width - title.length);
  const left = Math.floor(side / 2);
  const right = side - left;
  return `${"=".repeat(left)}${title}${"=".repeat(right)}`;
}

function printChatHeader(options) {
  const greeting = "Hola señor, que vamos a hacer hoy";
  console.log("");
  console.log(color("36;1", uiRule("JARVIS ONLINE")));
  console.log(`${color("32", "voz")}    ${greeting}`);
  console.log(`${color("32", "target")} ${options.target}`);
  console.log(`${color("32", "modo")}   ${options.mode}  |  comandos: /help /target /mode /voice on|off /exit`);
  console.log(color("36;1", uiRule()));
  console.log("");
}

function printChatHelp() {
  console.log([
    color("36;1", uiRule("AYUDA")),
    "Dime cualquier cosa en lenguaje natural. Si es tarea, la enruto al especialista correcto.",
    "",
    "Ejemplos:",
    '  arregla este bug y revisa el cambio',
    '  revisa este repo y dime que falta',
    '  crea un plan para mejorar Jarvis',
    '  diagnostico del setup',
    "",
    "Comandos:",
    "  /target <ruta>             cambia el proyecto objetivo",
    "  /mode auto|fast|full|council",
    "  /voice on|off              activa o silencia respuestas habladas",
    "  /dry-run on|off",
    "  /exit",
    color("36;1", uiRule())
  ].join("\n"));
}

function sayLocal(text, options = {}) {
  console.log(text);
  if (options.speak) speak(text);
}

function visibleOutput(raw) {
  const text = (raw || "").trim();
  if (!text) return "";
  const parsed = parseJsonObject(text);
  if (!parsed) return text;

  if (parsed.status === "dry_run") return JSON.stringify(parsed, null, 2);
  const extracted = extractText(parsed);
  return extracted || text;
}

function parseJsonObject(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function extractText(value) {
  if (!value) return "";
  if (typeof value === "string") return value.trim();
  if (Array.isArray(value)) return value.map(extractText).filter(Boolean).join("\n");
  if (typeof value !== "object") return "";

  if (typeof value.finalAssistantVisibleText === "string") return value.finalAssistantVisibleText.trim();
  if (typeof value.text === "string") return value.text.trim();
  if (typeof value.content === "string") return value.content.trim();
  if (typeof value.message === "string") return value.message.trim();
  if (typeof value.result === "string") return value.result.trim();
  if (typeof value.output === "string") return value.output.trim();
  if (Array.isArray(value.payloads)) return value.payloads.map(extractText).filter(Boolean).join("\n");
  if (Array.isArray(value.choices)) return value.choices.map(extractText).filter(Boolean).join("\n");
  if (value.message) return extractText(value.message);
  if (value.result) return extractText(value.result);
  if (value.response) return extractText(value.response);

  return "";
}

function statusOf(result) {
  if (result.error) return "failed";
  return result.status === 0 ? "succeeded" : "failed";
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}

function findExecutableInPath(name) {
  // Native resolver: walks PATH applying PATHEXT on Windows. Required because
  // `bash -lc command -v` under Git Bash on Windows misses .CMD/.cmd/.exe
  // shims that are normal Node/npm/global-bin install targets.
  const env = process["env"];
  const isWin = process.platform === "win32";
  const pathSep = isWin ? ";" : ":";
  const dirs = (env["PATH"] || "").split(pathSep).filter(Boolean);
  // On Windows try PATHEXT first so we prefer executable .CMD/.EXE over
  // extensionless shims (which spawn cannot execute natively).
  const exts = isWin
    ? (env["PATHEXT"] || ".COM;.EXE;.BAT;.CMD").split(";").concat([""])
    : [""];
  const hasExt = isWin && /\.[A-Za-z0-9]{1,4}$/.test(name);
  const candidateExts = hasExt ? [""] : exts;
  for (const dir of dirs) {
    for (const ext of candidateExts) {
      const full = `${dir}${isWin ? "\\" : "/"}${name}${ext}`;
      if (existsSync(full)) return full;
    }
  }
  return "";
}

function findExecutable(candidates) {
  for (const candidate of candidates) {
    if ((candidate.includes("/") || candidate.includes("\\")) && existsSync(candidate)) {
      return candidate;
    }
    const native = findExecutableInPath(candidate);
    if (native) return native;
    const result = spawnSync("bash", ["-lc", `command -v ${shellQuote(candidate)}`], { encoding: "utf8" });
    if (result.status === 0 && result.stdout.trim()) return result.stdout.trim();
  }
  return "";
}

function runSmall(cmd, args = []) {
  // Windows: spawn cannot execute .cmd/.bat directly. Route through
  // `cmd.exe /c` instead of `shell: true` to preserve argv quoting when paths
  // contain spaces (e.g. "C:\Users\Acer Nitro\...").
  if (process.platform === "win32" && /\.(cmd|bat)$/i.test(cmd)) {
    return spawnSync("cmd.exe", ["/c", cmd, ...args], {
      encoding: "utf8",
      timeout: 10000,
      maxBuffer: 1024 * 1024
    });
  }
  return spawnSync(cmd, args, {
    encoding: "utf8",
    timeout: 10000,
    maxBuffer: 1024 * 1024
  });
}

function checkLine(name, status, detail, required = false) {
  return { name, status, detail, required };
}

function runDoctor({ json = false } = {}) {
  ensureConfig();
  mkdirSync(RUNS_DIR, { recursive: true });

  // Windows-native names tried first (PATHEXT resolves .CMD/.cmd/.exe).
  const openclaw = findExecutable(["openclaw", "openclaw.cmd", "openclaw.CMD", "/home/emmanuel/.npm-global/bin/openclaw"]);
  const codex = findExecutable(["codex", "codex.cmd", "codex.CMD", "/home/emmanuel/.local/bin/codex", "/home/emmanuel/.npm-global/bin/codex"]);
  const claude = findExecutable(["claude", "claude.cmd", "claude.CMD", "/home/emmanuel/.npm-global/bin/claude"]);
  const qwen = findExecutable(["qwen", "qwen.cmd", "qwen.CMD", "/home/emmanuel/.local/bin/qwen"]);
  const multica = findExecutable(["multica", "D:/Emmanuel/.multica/bin/multica.exe", "/mnt/c/Users/Acer Nitro/.multica/bin/multica"]);
  const powershell = findExecutable(["powershell.exe"]);
  const jarvis = findExecutable(["jarvis"]);

  const checks = [
    checkLine("Node.js", "ok", process.version, true),
    checkLine("Jarvis home", existsSync(ROOT) ? "ok" : "missing", ROOT, true),
    checkLine("Dispatcher", existsSync(DISPATCHER) ? "ok" : "missing", DISPATCHER, true),
    checkLine("Config", existsSync(CONFIG_FILE) ? "ok" : "created", CONFIG_FILE),
    checkLine("jarvis command", jarvis ? "ok" : "warn", jarvis || "not on PATH; run ./install.sh"),
    checkLine("OpenClaw", openclaw ? versionDetail(openclaw, ["--version"]) : "missing", openclaw || "install/login required", true),
    checkLine("Codex", codex ? versionDetail(codex, ["--version"]) : "warn", codex || "optional adapter unavailable"),
    checkLine("Claude", claude ? versionDetail(claude, ["--version"]) : "warn", claude || "optional adapter unavailable"),
    checkLine("Qwen", qwen ? versionDetail(qwen, ["--version"]) : "warn", qwen || "optional adapter unavailable"),
    checkLine("Multica", multica ? versionDetail(multica, ["version"]) : "warn", multica || "optional agent platform unavailable"),
    checkLine("Windows voice", powershell ? "ok" : "warn", powershell || "voice commands need powershell.exe")
  ];

  if (openclaw) {
    const gateway = runSmall(openclaw, ["gateway", "status", "--json"]);
    checks.push(checkLine("OpenClaw gateway", gateway.status === 0 ? "ok" : "warn", gateway.status === 0 ? gatewayDetail(gateway.stdout) : compactOneLine(gateway.stderr || "gateway status unavailable")));
  }

  if (json) {
    console.log(JSON.stringify({ root: ROOT, config: CONFIG_FILE, checks }, null, 2));
    return checks;
  }

  console.log("Jarvis doctor");
  console.log(`Home: ${ROOT}`);
  for (const item of checks) {
    const mark = item.status === "ok" ? "OK" : item.status === "created" ? "OK" : item.required ? "MISS" : "WARN";
    console.log(`${mark.padEnd(5)} ${item.name.padEnd(18)} ${item.detail}`);
  }

  const missingRequired = checks.filter((item) => item.required && !["ok", "created"].includes(item.status));
  if (missingRequired.length > 0) {
    console.log("\nAccion: instala o autentica los requisitos MISS, luego ejecuta `jarvis setup`.");
  } else {
    console.log("\nJarvis esta listo para uso diario.");
  }

  return checks;
}

function versionDetail(cmd, args) {
  const result = runSmall(cmd, args);
  if (result.status !== 0) return "warn";
  return "ok";
}

function compactOneLine(text) {
  return String(text).replace(/\s+/g, " ").trim().slice(0, 180);
}

function gatewayDetail(text) {
  try {
    const data = JSON.parse(text);
    const service = data.service?.activeText || data.service?.status || "available";
    const bind = data.gateway?.bind || data.gateway?.url || "loopback";
    return `${service}, ${bind}`;
  } catch {
    return compactOneLine(text);
  }
}

function installLocalWrappers() {
  const home = process.env.HOME;
  if (!home) return { status: "warn", detail: "HOME no esta definido" };

  const binDir = join(home, ".local", "bin");
  mkdirSync(binDir, { recursive: true });
  const jarvisPath = join(binDir, "jarvis");
  const voicePath = join(binDir, "jarvis-voz");
  const wrapper = [
    "#!/usr/bin/env bash",
    `export JARVIS_HOME=${shellQuote(ROOT)}`,
    'exec node "$JARVIS_HOME/bin/jarvis-auto.mjs" "$@"',
    ""
  ].join("\n");
  const voiceWrapper = [
    "#!/usr/bin/env bash",
    `export JARVIS_HOME=${shellQuote(ROOT)}`,
    'exec node "$JARVIS_HOME/bin/jarvis-auto.mjs" --listen --speak "$@"',
    ""
  ].join("\n");

  writeFileSync(jarvisPath, wrapper);
  writeFileSync(voicePath, voiceWrapper);
  chmodSync(jarvisPath, 0o755);
  chmodSync(voicePath, 0o755);
  return { status: "ok", detail: `${jarvisPath}, ${voicePath}` };
}

function runSetup() {
  const config = ensureConfig();
  const wrappers = installLocalWrappers();

  console.log("Jarvis setup");
  console.log(`Home: ${ROOT}`);
  console.log(`Config: ${CONFIG_FILE}`);
  console.log(`Wrapper: ${wrappers.detail}`);
  console.log("");
  console.log("Uso diario:");
  console.log('  jarvis "arregla este bug y revisa el cambio"');
  console.log("  jarvis chat");
  console.log("  jarvis voz");
  console.log("  jarvis doctor");
  console.log("  jarvis improve");
  console.log("");
  console.log(`Voz: ${config.voice.style}. No clona voces de peliculas; usa una voz original configurable.`);
  console.log("");
  runDoctor();
}

function runImprove(args) {
  args.target = ROOT;
  args.mode = args.apply ? "full" : "council";
  args.prompt = args.apply
    ? [
      "Self-improvement apply mode for OpenClawJarvis.",
      "Audit this Jarvis setup, identify the highest-value safe improvement, implement the smallest correct change, verify it, and update docs.",
      "Do not touch secrets. Do not commit, push, deploy, or run destructive commands.",
      "Preserve user changes and keep the UX beginner-friendly."
    ].join(" ")
    : [
      "Self-improvement audit for OpenClawJarvis.",
      "Evaluate portability, beginner UX, routing quality, safety, voice setup, documentation, and maintainability.",
      "Return prioritized findings and a minimal safe improvement plan. Do not edit files in audit mode."
    ].join(" ");
  return runOnce(args.prompt, args);
}

function runVoiceCommand(args) {
  const action = args.voiceAction || "test";
  if (action === "list") return listVoices();
  if (action === "set") return setVoice(args);
  if (action === "test") {
    const config = ensureConfig();
    const sample = args.prompt || config.voice.sample;
    speak(sample);
    console.log("Voice test sent to Windows Speech.");
    return;
  }
  throw new Error(`Accion de voz invalida: ${action}. Usa list, set o test.`);
}

function localIntent(prompt, options = {}) {
  const p = normalize(prompt);
  const compact = p.replace(/[^\w\s/-]/g, "").replace(/\s+/g, " ").trim();

  if (/^(hola|hello|hi|hey|buenas|buenos dias|buenas tardes|buenas noches)( (jarvis|jaris))?$/.test(compact)) {
    sayLocal("Hola señor. Estoy listo; dime que quieres hacer y lo manejo.", options);
    return true;
  }

  if (/^(gracias|ok|okay|vale|listo|perfecto|test|smoke|prueba|d+)$/.test(compact)) {
    sayLocal("Recibido, señor. Sigo atento.", options);
    return true;
  }

  if (["help", "ayuda", "que puedes hacer", "comandos"].includes(compact)) {
    printChatHelp();
    return true;
  }

  if (["doctor", "diagnostico", "diagnóstico", "estado del setup", "health"].some((x) => p.includes(normalize(x)))) {
    runDoctor();
    return true;
  }

  if (["fecha", "hora", "que hora es", "qué hora es"].some((x) => p.includes(normalize(x)))) {
    console.log(new Date().toLocaleString("es-CO", { timeZone: "America/Bogota" }));
    return true;
  }

  if (["presupuesto", "budget", "tokens", "costo", "costos"].some((x) => p.includes(normalize(x)))) {
    runBudgetReport();
    return true;
  }

  return false;
}

function estimateTokens(text) {
  return Math.ceil(String(text).length / 4);
}

function readIfExists(path) {
  try {
    return existsSync(path) ? readFileSync(path, "utf8") : "";
  } catch {
    return "";
  }
}

function runBudgetReport() {
  const config = ensureConfig();
  const files = [
    "bin/jarvis-auto.mjs",
    "bin/jarvis-dispatch.mjs",
    "README.md",
    "QUICKSTART.md",
    "PORTABLE_SETUP.md",
    "VOICE.md",
    "SELF_IMPROVEMENT.md",
    "PENDIENTES.md",
    "config/jarvis-profile.json"
  ];

  const rows = files.map((file) => {
    const path = join(ROOT, file);
    const content = readIfExists(path);
    return { file, lines: content ? content.split(/\r?\n/).length : 0, tokens: estimateTokens(content) };
  });
  const total = rows.reduce((sum, row) => sum + row.tokens, 0);

  console.log("Jarvis budget report");
  console.log(`Default budget: ${config.cost?.defaultBudget || "economy"}`);
  console.log(`Prefer subscription CLI: ${config.cost?.preferSubscriptionCli ? "yes" : "no"}`);
  console.log(`Estimated Jarvis layer docs/code tokens: ~${total}`);
  console.log("");
  for (const row of rows.sort((a, b) => b.tokens - a.tokens).slice(0, 6)) {
    console.log(`${String(row.tokens).padStart(5)} tok  ${String(row.lines).padStart(4)} lines  ${row.file}`);
  }
  console.log("");
  console.log("Cost policy:");
  console.log("- Local commands answer help/doctor/date/budget without model calls.");
  console.log("- economy routes implementation through Claude plan + Codex implement/review.");
  console.log("- risky/max edits add extra subscription review before any API-backed fallback.");
  console.log("- voice uses local Windows Speech by default, not Realtime/API.");
}

function listVoices() {
  const result = spawnSync("powershell.exe", ["-NoProfile", "-Command", [
    "Add-Type -AssemblyName System.Speech",
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
    "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
  ].join("; ")], { encoding: "utf8", timeout: 10000 });

  if (result.status !== 0) {
    console.error("No pude listar voces. Windows Speech/PowerShell no esta disponible.");
    return;
  }

  console.log(result.stdout.trim() || "No se encontraron voces instaladas.");
}

function setVoice(args) {
  const config = ensureConfig();
  if (args.voiceName !== null) config.voice.voiceName = args.voiceName;
  if (Number.isFinite(args.voiceRate)) config.voice.rate = Math.max(-10, Math.min(10, args.voiceRate));
  if (Number.isFinite(args.voiceVolume)) config.voice.volume = Math.max(0, Math.min(100, args.voiceVolume));
  if (args.voiceStyle) config.voice.style = args.voiceStyle;
  writeConfig(config);
  console.log(`Voice config updated: ${CONFIG_FILE}`);
  console.log(`style=${config.voice.style}, voice=${config.voice.voiceName || "auto"}, rate=${config.voice.rate}, volume=${config.voice.volume}`);
}

function makeAutoRunDir() {
  const runId = `${new Date().toISOString().replace(/[:.]/g, "-")}-auto`;
  const runDir = join(RUNS_DIR, runId);
  mkdirSync(runDir, { recursive: true });
  return runDir;
}

async function runOnce(prompt, options) {
  const route = routePrompt(prompt, options);
  if (route.mode === "self-improvement" && !options.targetProvided) options.target = ROOT;
  route.roles = unique(route.roles);
  const runDir = makeAutoRunDir();
  const record = {
    prompt,
    target: options.target,
    dryRun: options.dryRun,
    speak: options.speak,
    route
  };

  writeFileSync(join(runDir, "route.json"), `${JSON.stringify(record, null, 2)}\n`);
  writeFileSync(join(runDir, "prompt.txt"), `${prompt}\n`);

  console.log(`[jarvis] target: ${options.target}`);
  console.log(`[jarvis] ruta: ${route.roles.join(" -> ")}`);
  console.log(`[jarvis] razon: ${route.reason}`);
  console.log(`[jarvis] run: ${runDir}`);

  const previousOutputs = [];
  let finalText = "";

  for (let i = 0; i < route.roles.length; i += 1) {
    const role = route.roles[i];
    const objective = buildStepObjective({
      prompt,
      route,
      role,
      stepIndex: i,
      stepCount: route.roles.length,
      target: options.target,
      previousOutputs
    });

    console.log(`\n[jarvis] paso ${i + 1}/${route.roles.length}: ${role}`);
    const result = runDispatch({
      role,
      objective,
      target: options.target,
      dryRun: options.dryRun
    });

    const out = result.stdout || "";
    const err = result.error
      ? [result.stderr || "", result.error.message].filter(Boolean).join("\n")
      : result.stderr || "";
    const combined = [out, err].filter(Boolean).join("\n");
    const visible = visibleOutput(out);
    const failed = result.error || result.status !== 0;

    writeFileSync(join(runDir, `${String(i + 1).padStart(2, "0")}-${role}.stdout.txt`), out);
    writeFileSync(join(runDir, `${String(i + 1).padStart(2, "0")}-${role}.stderr.txt`), err);
    writeFileSync(join(runDir, `${String(i + 1).padStart(2, "0")}-${role}.json`), `${JSON.stringify({
      role,
      status: statusOf(result),
      exitCode: result.status,
      signal: result.signal,
      error: result.error?.message
    }, null, 2)}\n`);

    if (visible) process.stdout.write(ensureTrailingNewline(visible));
    if (failed && err) process.stderr.write(ensureTrailingNewline(err));

    previousOutputs.push({
      role,
      status: statusOf(result),
      output: visible || combined
    });
    finalText = visible || combined || finalText;

    if (failed) {
      const fallback = fallbackRole(role);
      if (fallback && !options.dryRun) {
        console.log(`\n[jarvis] fallback: ${role} -> ${fallback}`);
        const fallbackObjective = buildStepObjective({
          prompt: `${prompt}\n\nFallback note: ${role} failed; continue with ${fallback}.`,
          route,
          role: fallback,
          stepIndex: i,
          stepCount: route.roles.length,
          target: options.target,
          previousOutputs
        });
        const fallbackResult = runDispatch({
          role: fallback,
          objective: fallbackObjective,
          target: options.target,
          dryRun: false
        });
        const fallbackOut = fallbackResult.stdout || "";
        const fallbackErr = fallbackResult.error
          ? [fallbackResult.stderr || "", fallbackResult.error.message].filter(Boolean).join("\n")
          : fallbackResult.stderr || "";
        const fallbackVisible = visibleOutput(fallbackOut);
        const fallbackFailed = fallbackResult.error || fallbackResult.status !== 0;

        writeFileSync(join(runDir, `${String(i + 1).padStart(2, "0")}-${role}-fallback-${fallback}.stdout.txt`), fallbackOut);
        writeFileSync(join(runDir, `${String(i + 1).padStart(2, "0")}-${role}-fallback-${fallback}.stderr.txt`), fallbackErr);
        if (fallbackVisible) process.stdout.write(ensureTrailingNewline(fallbackVisible));
        if (fallbackFailed && fallbackErr) process.stderr.write(ensureTrailingNewline(fallbackErr));

        previousOutputs.push({
          role: fallback,
          status: statusOf(fallbackResult),
          output: fallbackVisible || [fallbackOut, fallbackErr].filter(Boolean).join("\n")
        });
        finalText = fallbackVisible || fallbackOut || finalText;
        if (!fallbackFailed) continue;
      }
      console.log(`\n[jarvis] detenido: ${role} fallo con exit ${result.status ?? "unknown"}.`);
      break;
    }
  }

  const transcript = previousOutputs
    .map((item) => `## ${item.role} (${item.status})\n\n${item.output}`)
    .join("\n\n");
  writeFileSync(join(runDir, "transcript.md"), `${transcript}\n`);

  const lastStatus = previousOutputs.at(-1)?.status || "not_started";
  console.log(`\n[jarvis] status: ${lastStatus}`);
  console.log(`[jarvis] logs: ${runDir}`);

  if (options.speak) speak(compactForSpeech(finalText || `Jarvis termino con estado ${lastStatus}.`));

  return { status: lastStatus, runDir, route };
}

function compactForSpeech(text) {
  const clean = text
    .replace(/\s+/g, " ")
    .replace(/[{}[\]"`]/g, "")
    .trim();
  if (clean.length <= 700) return clean;
  return `${clean.slice(0, 700)}. Respuesta completa en los logs de Jarvis.`;
}

function speak(text) {
  const config = readConfig();
  const script = [
    "Add-Type -AssemblyName System.Speech",
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
    "$installed = @($s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name })",
    "$name = $env:JARVIS_VOICE_NAME",
    "$preferred = @()",
    "if ($env:JARVIS_VOICE_PREFERRED) { $preferred = $env:JARVIS_VOICE_PREFERRED | ConvertFrom-Json }",
    "if ($name -and ($installed -contains $name)) { $s.SelectVoice($name) } else { foreach ($v in $preferred) { if ($installed -contains $v) { $s.SelectVoice($v); break } } }",
    "$s.Rate = [int]$env:JARVIS_VOICE_RATE",
    "$s.Volume = [int]$env:JARVIS_VOICE_VOLUME",
    "$text = [Console]::In.ReadToEnd()",
    "$s.Speak($text)"
  ].join("; ");

  const result = spawnSync("powershell.exe", ["-NoProfile", "-Command", script], {
    encoding: "utf8",
    input: text,
    timeout: 30000,
    env: {
      ...process.env,
      JARVIS_VOICE_NAME: config.voice.voiceName || "",
      JARVIS_VOICE_RATE: String(config.voice.rate ?? -1),
      JARVIS_VOICE_VOLUME: String(config.voice.volume ?? 100),
      JARVIS_VOICE_PREFERRED: JSON.stringify(config.voice.preferredVoiceNames || [])
    }
  });

  if (result.status !== 0) {
    console.error("[jarvis] voz no disponible en este entorno.");
  }
}

function listen() {
  const script = [
    "Add-Type -AssemblyName System.Speech",
    "$r = New-Object System.Speech.Recognition.SpeechRecognitionEngine",
    "$r.SetInputToDefaultAudioDevice()",
    "$g = New-Object System.Speech.Recognition.DictationGrammar",
    "$r.LoadGrammar($g)",
    "Write-Error 'Escuchando por 12 segundos...'",
    "$res = $r.Recognize([TimeSpan]::FromSeconds(12))",
    "if ($res -ne $null) { [Console]::Out.Write($res.Text) }"
  ].join("; ");

  const result = spawnSync("powershell.exe", ["-NoProfile", "-Command", script], {
    encoding: "utf8",
    timeout: 20000
  });

  if (result.status !== 0 || !result.stdout.trim()) {
    throw new Error("No pude capturar voz. Revisa microfono/idioma de Windows Speech o usa texto: jarvis \"...\".");
  }

  return result.stdout.trim();
}

async function chatLoop(options) {
  const config = readConfig();
  const greeting = "Hola señor, que vamos a hacer hoy";
  if (config.ux?.speakChatReplies !== false) options.speak = true;
  if (config.ux?.terminalUi !== false) printChatHeader(options);
  else {
    console.log("Jarvis chat. Escribe /help, /target <ruta>, /mode auto|fast|full|council, /exit.");
    console.log(`Target actual: ${options.target}`);
  }
  if (config.ux?.voiceGreeting !== false) speak(greeting);

  const rl = readline.createInterface({ input, output });

  try {
    while (true) {
      const line = (await rl.question(color("36;1", "Jarvis > "))).trim();
      if (!line) continue;
      if (line === "/exit" || line === "/quit") break;
      if (line === "/help") {
        printChatHelp();
        continue;
      }
      if (line.startsWith("/target ")) {
        options.target = resolve(line.slice("/target ".length).trim());
        console.log(`${color("32", "target")} ${options.target}`);
        continue;
      }
      if (line.startsWith("/mode ")) {
        options.mode = line.slice("/mode ".length).trim();
        console.log(`${color("32", "modo")} ${options.mode}`);
        continue;
      }
      if (line === "/voice on") {
        options.speak = true;
        sayLocal("Voz activada.", options);
        continue;
      }
      if (line === "/voice off") {
        options.speak = false;
        console.log("Voz desactivada.");
        continue;
      }
      if (line === "/dry-run on") {
        options.dryRun = true;
        console.log(`${color("33", "dry-run")} activo`);
        continue;
      }
      if (line === "/dry-run off") {
        options.dryRun = false;
        console.log(`${color("33", "dry-run")} desactivado`);
        continue;
      }
      if (localIntent(line, options)) continue;

      await runOnce(line, options);
    }
  } finally {
    rl.close();
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    usage();
    return;
  }

  ensureConfig();

  if (args.command === "setup") {
    runSetup();
    return;
  }

  if (args.command === "doctor") {
    runDoctor();
    return;
  }

  if (args.command === "budget") {
    runBudgetReport();
    return;
  }

  if (args.command === "voice") {
    runVoiceCommand(args);
    return;
  }

  if (args.command === "improve") {
    await runImprove(args);
    return;
  }

  if (args.command === "reels") {
    if (!args.reelUrl) {
      console.error("uso: jarvis reels <url> [--lang es]");
      process.exit(2);
    }
    const repoRoot = resolve(ROOT, "..", "..");
    const coreDir = join(repoRoot, "core");
    const venvWin = join(repoRoot, ".venv", "Scripts", "python.exe");
    const venvNix = join(repoRoot, ".venv", "bin", "python");
    const py = existsSync(venvWin) ? venvWin
      : existsSync(venvNix) ? venvNix
      : (process.platform === "win32" ? "python.exe" : "python3");
    const pyArgs = ["-m", "jarvis.pipelines.reels", args.reelUrl];
    if (args.reelLang) pyArgs.push("--lang", args.reelLang);
    const result = spawnSync(py, pyArgs, { cwd: coreDir, stdio: "inherit" });
    process.exit(result.status ?? 0);
  }

  if (["start", "stop", "status"].includes(args.command)) {
    const lifecycle = join(dirname(fileURLToPath(import.meta.url)), "jarvis-lifecycle.mjs");
    const result = spawnSync(process.execPath, [lifecycle, args.command], { stdio: "inherit" });
    process.exit(result.status ?? 0);
  }

  if (!["auto", "fast", "full", "council"].includes(args.mode)) {
    throw new Error(`Modo invalido: ${args.mode}`);
  }

  if (args.listen) {
    console.error("[jarvis] escuchando...");
    args.prompt = listen();
    console.log(`[jarvis] voz capturada: ${args.prompt}`);
  }

  if (args.chat || !args.prompt) {
    await chatLoop(args);
    return;
  }

  if (localIntent(args.prompt)) return;

  await runOnce(args.prompt, args);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
