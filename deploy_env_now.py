#!/usr/bin/env python3
"""Upload .env and deploy to server."""
import sys
import time
from pathlib import Path

import paramiko

HOST = "47.94.210.217"
PASSWORD = "Lhw207905"
PROJECT = "/opt/AI-Companion-OS"


def connect():
    for user in ("root", "admin"):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(HOST, username=user, password=PASSWORD, timeout=30)
            print(f"Connected as {user}")
            return client, user
        except Exception as exc:
            print(f"{user} failed: {exc}")
    sys.exit(1)


def run(client, cmd, timeout=1200):
    print(f"\n>>> {cmd[:100]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    text = (out + err).strip()
    if text:
        print(text[-2500:])
    print(f"[exit: {code}]")
    return code, text


def main():
    env_content = Path(".env").read_text(encoding="utf-8")
    client, user = connect()
    sudo = f"echo '{PASSWORD}' | sudo -S"

    run(client, f"{sudo} mkdir -p /opt")
    run(
        client,
        f"cd /opt && {sudo} git clone https://github.com/wen207905-del/AI-Companion-OS.git "
        f"2>/dev/null || (cd {PROJECT} && git pull origin main)",
    )
    run(client, f"{sudo} chown -R {user}:{user} {PROJECT} 2>/dev/null || true")

    sftp = client.open_sftp()
    with sftp.open(f"{PROJECT}/.env", "w") as f:
        f.write(env_content)
    sftp.close()
    run(client, f"{sudo} chmod 600 {PROJECT}/.env")
    print(".env uploaded OK")

    run(client, f"cd {PROJECT} && {sudo} docker compose up -d --build", timeout=1800)
    print("Waiting 30s for healthcheck...")
    time.sleep(30)
    run(client, f"cd {PROJECT} && {sudo} docker compose ps")
    run(client, "curl -s http://127.0.0.1/api/health")
    client.close()
    print("\nDeploy complete. Open http://47.94.210.217/")


if __name__ == "__main__":
    main()
