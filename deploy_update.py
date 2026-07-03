#!/usr/bin/env python3
"""Pull latest code, rebuild, verify deployment."""
import paramiko
import time
from pathlib import Path

HOST = "47.94.210.217"
PASSWORD = "Lhw207905"
PROJECT = "/opt/AI-Companion-OS"


def run(client, cmd, timeout=1800):
    print(f"\n>>> {cmd[:100]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    text = (out + err).strip()
    if text:
        print(text[-3000:])
    print(f"[exit: {code}]")
    return code, text


def main():
    env_content = Path(".env").read_text(encoding="utf-8")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=PASSWORD, timeout=30)

    run(client, f"chown -R admin:admin {PROJECT}")
    run(client, f"cd {PROJECT} && git config --global --add safe.directory {PROJECT}")

    for attempt in range(3):
        code, _ = run(client, f"cd {PROJECT} && git fetch origin && git reset --hard origin/main")
        if code == 0:
            break
        time.sleep(8)

    sftp = client.open_sftp()
    with sftp.open(f"{PROJECT}/.env", "w") as f:
        f.write(env_content)
    sftp.close()
    run(client, f"chmod 600 {PROJECT}/.env")
    print(".env synced")

    run(client, f"cd {PROJECT} && docker compose up -d --build", timeout=1800)
    print("Waiting 35s...")
    time.sleep(35)

    run(client, f"cd {PROJECT} && docker compose ps")
    run(client, "curl -s http://127.0.0.1/api/health")
    run(client, "curl -sI http://127.0.0.1/ | head -5")
    run(client, f"cd {PROJECT} && git log -1 --oneline")
    run(client, f"test -f {PROJECT}/config/status_mod/manifest.yaml && grep variant {PROJECT}/config/status_mod/manifest.yaml")

    client.close()
    print("\n=== Done ===")
    print("Open: http://47.94.210.217/")


if __name__ == "__main__":
    main()
