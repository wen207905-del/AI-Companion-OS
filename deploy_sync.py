#!/usr/bin/env python3
"""Sync latest files to server via SFTP when git pull fails."""
import os
import paramiko
import time
from pathlib import Path

HOST = "47.94.210.217"
PASSWORD = "Lhw207905"
PROJECT = "/opt/AI-Companion-OS"
ROOT = Path(__file__).resolve().parent

FILES = """
config/character_templates/ye_ruxue.jpg
config/status_mod/manifest.yaml
config/status_mod/outfits.yaml
config/visual/character_image_prompts.yaml
config/visual/character_nude_prompts.md
config/visual/character_photo_templates.yaml
docker-compose.yml
v2/backend/api/image_routes.py
v2/backend/api/rest_routes.py
v2/backend/api/ws_routes.py
v2/backend/chat/context_builder.py
v2/backend/chat/group_service.py
v2/backend/chat/history_loader.py
v2/backend/chat/prompt_builder.py
v2/backend/chat/stream_delivery.py
v2/backend/config.py
v2/backend/engine/absence.py
v2/backend/engine/emotion_engine.py
v2/backend/image/__init__.py
v2/backend/image/album_store.py
v2/backend/image/chat_photo.py
v2/backend/image/config.py
v2/backend/image/exposure_fallback.py
v2/backend/image/identity_loader.py
v2/backend/image/intent_detector.py
v2/backend/image/orchestrator.py
v2/backend/image/prompt_composer.py
v2/backend/image/prompt_loader.py
v2/backend/image/router.py
v2/backend/image/scene_parser.py
v2/backend/image/siliconflow.py
v2/backend/main.py
v2/backend/mod/__init__.py
v2/backend/mod/config_loader.py
v2/backend/mod/outfit_state.py
v2/backend/mod/reproductive.py
v2/backend/mod/status_block.py
v2/backend/mod/user_status.py
v2/backend/runtime/__init__.py
v2/backend/runtime/life_scheduler.py
v2/frontend/src/components/ChatInput.svelte
v2/frontend/src/components/MessageBubble.svelte
v2/frontend/src/pages/CharacterPanel.svelte
v2/frontend/src/pages/Chat.svelte
v2/frontend/src/stores/chat.js
""".strip().splitlines()


def ensure_remote_dir(sftp, remote_dir: str):
    parts = remote_dir.replace("\\", "/").split("/")
    path = ""
    for part in parts:
        if not part:
            continue
        path += "/" + part
        try:
            sftp.stat(path)
        except OSError:
            sftp.mkdir(path)


def run(client, cmd, timeout=1800):
    print(f">>> {cmd[:90]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    text = (out + err).strip()
    if text:
        print(text[-2000:])
    print(f"[exit: {code}]")
    return code


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=PASSWORD, timeout=30)
    sftp = client.open_sftp()

    uploaded = 0
    for rel in FILES:
        rel = rel.strip()
        if not rel:
            continue
        local = ROOT / rel.replace("/", os.sep)
        if not local.is_file():
            print(f"SKIP missing: {rel}")
            continue
        remote = f"{PROJECT}/{rel.replace(chr(92), '/')}"
        ensure_remote_dir(sftp, os.path.dirname(remote))
        sftp.put(str(local), remote)
        uploaded += 1
        print(f"OK {rel}")

    with sftp.open(f"{PROJECT}/.env", "w") as f:
        f.write((ROOT / ".env").read_text(encoding="utf-8"))
    sftp.close()
    print(f"Uploaded {uploaded} files + .env")

    run(client, f"chown -R admin:admin {PROJECT}")
    run(client, f"cd {PROJECT} && docker compose up -d --build --no-cache api web", timeout=2400)
    print("Waiting 40s...")
    time.sleep(40)
    run(client, f"cd {PROJECT} && docker compose ps")
    run(client, "curl -s http://127.0.0.1/api/health")
    run(client, f"test -f {PROJECT}/config/status_mod/manifest.yaml && grep variant {PROJECT}/config/status_mod/manifest.yaml")
    client.close()
    print("\nReady: http://47.94.210.217/")


if __name__ == "__main__":
    main()
