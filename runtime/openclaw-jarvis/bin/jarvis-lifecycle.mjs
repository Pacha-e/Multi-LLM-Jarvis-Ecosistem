#!/usr/bin/env node
/**
 * jarvis-lifecycle — start/stop/status reproducible for the FastAPI core.
 *
 * Usage (delegated from jarvis-auto.mjs):
 *   node jarvis-lifecycle.mjs start [--port 8000] [--host 127.0.0.1]
 *   node jarvis-lifecycle.mjs stop
 *   node jarvis-lifecycle.mjs status
 *
 * Files:
 *   <repo>/runtime/openclaw-jarvis/var/jarvis.pid   PID of uvicorn child
 *   <repo>/runtime/openclaw-jarvis/var/jarvis.log   stdout+stderr append
 *
 * Security:
 *   - Spawns python from PATH (no shell: true).
 *   - No tokens read or written.
 *   - PID/log paths are repo-local and gitignored.
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync, openSync, unlinkSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const RUNTIME_DIR = resolve(dirname(__filename), "..");        // runtime/openclaw-jarvis
const REPO_ROOT  = resolve(RUNTIME_DIR, "..", "..");           // Multi-LLM-Jarvis-Ecosistem
const CORE_DIR   = resolve(REPO_ROOT, "core");
const VAR_DIR    = resolve(RUNTIME_DIR, "var");
const PID_FILE   = resolve(VAR_DIR, "jarvis.pid");
const LOG_FILE   = resolve(VAR_DIR, "jarvis.log");

const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 8000;

function ensureVar() { mkdirSync(VAR_DIR, { recursive: true }); }

function readPid() {
  if (!existsSync(PID_FILE)) return null;
  const raw = readFileSync(PID_FILE, "utf8").trim();
  const pid = Number(raw);
  return Number.isFinite(pid) && pid > 0 ? pid : null;
}

function isAlive(pid) {
  if (!pid) return false;
  try { process.kill(pid, 0); return true; }
  catch (e) { return e.code === "EPERM"; }
}

function parseArgs(argv) {
  const out = { host: DEFAULT_HOST, port: DEFAULT_PORT };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--port") out.port = Number(argv[++i]);
    else if (a === "--host") out.host = argv[++i];
  }
  return out;
}

function pythonExe() {
  // Prefer a venv that matches the current OS. In WSL2, a Windows venv under
  // /mnt/c may exist but cannot run as the FastAPI interpreter.
  const venvWin = resolve(REPO_ROOT, ".venv", "Scripts", "python.exe");
  const venvNix = resolve(REPO_ROOT, ".venv", "bin", "python");
  if (process.platform === "win32" && existsSync(venvWin)) return venvWin;
  if (process.platform !== "win32" && existsSync(venvNix)) return venvNix;
  return process.platform === "win32" ? "python.exe" : "python3";
}

async function httpHealth(host, port) {
  const url = `http://${host}:${port}/health`;
  try {
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) return { ok: false, status: res.status };
    const body = await res.json().catch(() => ({}));
    return { ok: true, body };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

function sleepSync(ms) {
  const sab = new Int32Array(new SharedArrayBuffer(4));
  Atomics.wait(sab, 0, 0, ms);
}

function tailLog(lines = 12) {
  if (!existsSync(LOG_FILE)) return "";
  const all = readFileSync(LOG_FILE, "utf8").split(/\r?\n/);
  return all.slice(-lines).join("\n");
}

function cmdStart(opts) {
  ensureVar();
  const existing = readPid();
  if (isAlive(existing)) {
    console.log(`[jarvis] already running (pid=${existing}). status: use 'jarvis status'.`);
    return 0;
  }
  if (existing) { try { unlinkSync(PID_FILE); } catch {} } // stale

  const py = pythonExe();
  const args = ["-m", "uvicorn", "jarvis.main:app", "--host", opts.host, "--port", String(opts.port)];
  const out = openSync(LOG_FILE, "a");
  const err = openSync(LOG_FILE, "a");
  const child = spawn(py, args, {
    cwd: CORE_DIR,
    detached: true,
    stdio: ["ignore", out, err],
    windowsHide: true,
  });
  child.unref();
  writeFileSync(PID_FILE, String(child.pid));

  // Early-death check: uvicorn import errors surface within ~2s.
  sleepSync(2500);
  if (!isAlive(child.pid)) {
    try { unlinkSync(PID_FILE); } catch {}
    console.error(`[jarvis] FAILED to start (pid ${child.pid} exited). Last log:`);
    console.error(tailLog());
    return 1;
  }
  console.log(`[jarvis] started pid=${child.pid} on http://${opts.host}:${opts.port}`);
  console.log(`[jarvis] log: ${LOG_FILE}`);
  return 0;
}

function cmdStop() {
  const pid = readPid();
  if (!pid) { console.log("[jarvis] no pidfile; not running."); return 0; }
  if (!isAlive(pid)) {
    try { unlinkSync(PID_FILE); } catch {}
    console.log(`[jarvis] stale pid ${pid} cleaned.`);
    return 0;
  }
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "inherit" });
  } else {
    try { process.kill(pid, "SIGTERM"); } catch {}
  }
  try { unlinkSync(PID_FILE); } catch {}
  console.log(`[jarvis] stopped pid=${pid}.`);
  return 0;
}

async function cmdStatus(opts) {
  const pid = readPid();
  const alive = isAlive(pid);
  console.log(`pid:    ${pid ?? "-"}`);
  console.log(`alive:  ${alive ? "yes" : "no"}`);
  console.log(`host:   ${opts.host}:${opts.port}`);
  const health = await httpHealth(opts.host, opts.port);
  console.log(`health: ${health.ok ? "ok" : "down"}${health.error ? ` (${health.error})` : ""}`);
  if (health.body) console.log(`body:   ${JSON.stringify(health.body)}`);
  return alive && health.ok ? 0 : 1;
}

const [, , cmd, ...rest] = process.argv;
const opts = parseArgs(rest);
let code = 0;
switch (cmd) {
  case "start":  code = cmdStart(opts); break;
  case "stop":   code = cmdStop(); break;
  case "status": code = await cmdStatus(opts); break;
  default:
    console.log("usage: jarvis-lifecycle.mjs {start|stop|status} [--port N] [--host H]");
    code = 2;
}
process.exit(code);
