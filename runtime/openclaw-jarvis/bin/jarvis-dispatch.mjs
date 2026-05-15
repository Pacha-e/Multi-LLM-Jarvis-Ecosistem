#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.JARVIS_HOME ? resolve(process.env.JARVIS_HOME) : resolve(SCRIPT_DIR, "..");
const RUNS_DIR = join(ROOT, "runs");

const openClawAgentRoles = new Set(["orion", "kiro", "nova", "spark", "iris"]);
const subscriptionRoles = new Set([
  "claude-plan",
  "claude-architect",
  "claude-review",
  "codex-plan",
  "codex-implement",
  "codex-review"
]);
const cliRoles = new Set(["kiro-cli", "claude", "codex", "codex-write", "gemini", "qwen", "aider", "multica", "opencode", ...subscriptionRoles]);
const roles = new Set([...openClawAgentRoles, ...cliRoles]);

function usage() {
  console.log(`Usage:
  jarvis-dispatch --role <orion|kiro|nova|spark|iris|claude-plan|codex-implement|codex-review|kiro-cli|claude|codex|gemini|qwen|aider|multica> --objective <text> [--target <path>] [--dry-run]

Examples:
  jarvis-dispatch --role spark --objective "Implement focused fix" --target /repo --dry-run
  jarvis-dispatch --role iris --objective "Review this repo" --target /repo
  jarvis-dispatch --role aider --objective "Apply a focused edit" --target /repo`);
}

function parseArgs(argv) {
  const out = { target: process.cwd(), dryRun: false };
  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") out.help = true;
    else if (arg === "--dry-run") out.dryRun = true;
    else if (arg === "--role") out.role = argv[++i];
    else if (arg === "--objective") out.objective = argv[++i];
    else if (arg === "--target") out.target = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return out;
}

function buildPrompt(role, objective, target) {
  return [
    `OpenClaw Jarvis delegated specialist. Role=${role}. Target=${target}.`,
    "",
    "Objective:",
    objective,
    "",
    "Rules: preserve unrelated changes; never print secrets; smoke/no-op => no tools; output compact status/summary/evidence/changed_files/risks/next_handoff; if blocked, name blocker+smallest next action."
  ].join("\n");
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}

function findExecutable(candidates) {
  for (const candidate of candidates) {
    if (candidate.includes("/") && existsSync(candidate)) return candidate;
    const result = spawnSync("bash", ["-lc", `command -v ${shellQuote(candidate)}`], { encoding: "utf8" });
    if (result.status === 0 && result.stdout.trim()) return result.stdout.trim();
  }
  return candidates[0];
}

function commandFor(role, prompt, target, runId) {
  if (openClawAgentRoles.has(role)) {
    return {
      cmd: findExecutable(["openclaw", "/home/emmanuel/.npm-global/bin/openclaw"]),
      args: [
        "agent",
        "--local",
        "--agent",
        role,
        "--session-id",
        runId,
        "--message",
        prompt,
        "--json",
        "--thinking",
        "off",
        "--timeout",
        "240"
      ],
      cwd: target,
      env: envForGoogleProvider()
    };
  }

  switch (role) {
    case "kiro-cli":
      return {
        cmd: findExecutable(["kiro-cli", "C:/Users/Acer Nitro/AppData/Local/Kiro-Cli/kiro-cli.exe", "/home/emmanuel/.local/bin/kiro-cli"]),
        args: ["chat", "--no-interactive", prompt],
        cwd: target
      };
    case "claude":
    case "claude-plan":
    case "claude-architect":
    case "claude-review":
      return {
        cmd: findExecutable(["claude", "/home/emmanuel/.npm-global/bin/claude"]),
        args: ["--print", "--output-format", "json", "--permission-mode", "plan", prompt],
        cwd: target
      };
    case "codex":
    case "codex-plan":
    case "codex-review":
      return {
        cmd: findExecutable(["codex", "/home/emmanuel/.local/bin/codex", "/home/emmanuel/.npm-global/bin/codex"]),
        args: ["exec", "--skip-git-repo-check", "--sandbox", "read-only", prompt],
        cwd: target
      };
    case "codex-write":
    case "codex-implement":
      return {
        cmd: findExecutable(["codex", "/home/emmanuel/.local/bin/codex", "/home/emmanuel/.npm-global/bin/codex"]),
        args: ["exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
        cwd: target
      };
    case "gemini":
      return {
        cmd: findExecutable(["/home/emmanuel/ai-system/scripts/gemini-with-fallback.sh", "gemini"]),
        args: [prompt],
        cwd: target
      };
    case "qwen":
      return {
        cmd: findExecutable(["qwen", "/home/emmanuel/.local/bin/qwen"]),
        args: ["--approval-mode", "plan", "-p", prompt, "--output-format", "json"],
        cwd: target
      };
    case "aider":
      return {
        cmd: findExecutable(["aider", "/home/emmanuel/.local/bin/aider"]),
        args: [
          "--model",
          "gemini/gemini-2.5-flash",
          "--editor-model",
          "gemini/gemini-2.5-flash",
          "--no-check-update",
          "--no-auto-commits",
          "--no-dirty-commits",
          "--yes-always",
          "--message",
        prompt,
        "--exit"
        ],
        cwd: target,
        env: envForGoogleProvider()
      };
    case "multica":
      return {
        cmd: findExecutable(["multica", "D:/Emmanuel/.multica/bin/multica.exe", "/mnt/c/Users/Acer Nitro/.multica/bin/multica"]),
        args: ["agent", "create", "--help"],
        cwd: target
      };
    case "opencode":
      return {
        cmd: findExecutable(["opencode", "/c/Users/Acer Nitro/AppData/Roaming/npm/opencode"]),
        args: ["run", "--print", prompt],
        cwd: target
      };
    default:
      throw new Error(`Unsupported role: ${role}`);
  }
}

function envForGoogleProvider() {
  if (process.env.GEMINI_API_KEY) return {};
  try {
    const secrets = JSON.parse(readFileSync("/home/emmanuel/.openclaw/secrets.json", "utf8"));
    const apiKey = secrets?.models?.providers?.google?.apiKey;
    return typeof apiKey === "string" && apiKey.length > 0 ? { GEMINI_API_KEY: apiKey } : {};
  } catch {
    return {};
  }
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    usage();
    return;
  }
  if (!args.role || !roles.has(args.role)) {
    throw new Error(`Missing or invalid --role. Expected one of: ${[...roles].join(", ")}`);
  }
  if (!args.objective) {
    throw new Error("Missing --objective");
  }

  const target = resolve(args.target);
  const prompt = buildPrompt(args.role, args.objective, target);
  const runId = `${new Date().toISOString().replace(/[:.]/g, "-")}-${args.role}`;
  const command = commandFor(args.role, prompt, target, runId);
  const commandRecord = {
    cmd: command.cmd,
    args: command.args,
    cwd: command.cwd
  };
  const runDir = join(RUNS_DIR, runId);
  mkdirSync(runDir, { recursive: true });
  writeFileSync(join(runDir, "prompt.txt"), prompt);
  writeFileSync(join(runDir, "command.json"), `${JSON.stringify(commandRecord, null, 2)}\n`);

  if (args.dryRun) {
    console.log(JSON.stringify({ status: "dry_run", runDir, command: commandRecord }, null, 2));
    return;
  }

  const result = spawnSync(command.cmd, command.args, {
    cwd: command.cwd,
    encoding: "utf8",
    env: { ...process.env, ...(command.env || {}) }
  });

  writeFileSync(join(runDir, "stdout.txt"), result.stdout || "");
  writeFileSync(join(runDir, "stderr.txt"), result.stderr || "");
  writeFileSync(join(runDir, "result.json"), `${JSON.stringify({
    status: result.status === 0 ? "succeeded" : "failed",
    exitCode: result.status,
    signal: result.signal,
    runDir
  }, null, 2)}\n`);

  process.stdout.write(result.stdout || "");
  process.stderr.write(result.stderr || "");
  process.exit(result.status ?? 1);
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  usage();
  process.exit(2);
}
