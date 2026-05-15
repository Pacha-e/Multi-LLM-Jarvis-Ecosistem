#!/usr/bin/env python3
"""Push all new/modified JARVIS files to GitHub via gh CLI.
Run after: gh auth login --scopes repo
OR after updating fine-grained PAT with Contents:write
"""
import subprocess, json, base64, os, sys

GH = r"C:\Program Files\GitHub CLI\gh.exe"
REPO = "Pacha-e/Multi-LLM-Jarvis-Ecosistem"
BASE = os.path.dirname(os.path.abspath(__file__))
COMMIT_MSG = "feat: personas system, intent router, WSL2 service, persona API endpoints, EAFIT docs"

FILES = [
    ".gitignore",
    "run.py",
    "requirements.txt",
    "env.example",
    "README.md",
    "jarvis/agent/core.py",
    "jarvis/agent/personas.py",
    "jarvis/agent/router.py",
    "jarvis/agent/rag.py",
    "jarvis/main.py",
    "jarvis/integrations/__init__.py",
    "jarvis/integrations/telegram_bot.py",
    "jarvis/voice/wake_word.py",
    "scripts/jarvis.service",
    "scripts/setup_wsl.sh",
    "test_jarvis.py",
    "docs/informe_proyecto.md",
]


def get_sha(path):
    r = subprocess.run(
        [GH, "api", f"repos/{REPO}/contents/{path}"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        try:
            return json.loads(r.stdout).get("sha")
        except Exception:
            pass
    return None


def push_file(local_path, remote_path, msg):
    full_path = os.path.join(BASE, local_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        print(f"  SKIP (not found): {local_path}")
        return False

    content = open(full_path, "rb").read()
    b64 = base64.b64encode(content).decode()
    sha = get_sha(remote_path)

    payload = {"message": msg, "content": b64}
    if sha:
        payload["sha"] = sha

    r = subprocess.run(
        [GH, "api", "--method", "PUT",
         f"repos/{REPO}/contents/{remote_path}",
         "--input", "-"],
        input=json.dumps(payload),
        capture_output=True, text=True
    )
    ok = r.returncode == 0
    status = "OK" if ok else "FAIL"
    extra = "" if ok else f" -- {r.stderr.strip()[:120]}"
    print(f"  {status}: {remote_path}{extra}")
    return ok


def main():
    print(f"\nPushing {len(FILES)} files to {REPO}...\n")
    ok_count = 0
    for f in FILES:
        if push_file(f, f, COMMIT_MSG):
            ok_count += 1
    print(f"\nDone: {ok_count}/{len(FILES)} files pushed.")

    # Delete old gitignore.txt if it exists
    sha = get_sha("gitignore.txt")
    if sha:
        payload = {"message": "chore: remove gitignore.txt (replaced by .gitignore)", "sha": sha}
        r = subprocess.run(
            [GH, "api", "--method", "DELETE",
             f"repos/{REPO}/contents/gitignore.txt",
             "--input", "-"],
            input=json.dumps(payload),
            capture_output=True, text=True
        )
        if r.returncode == 0:
            print("  OK: Deleted gitignore.txt")
        else:
            print(f"  FAIL: Could not delete gitignore.txt: {r.stderr[:80]}")


if __name__ == "__main__":
    main()
