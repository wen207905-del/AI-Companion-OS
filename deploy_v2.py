#!/usr/bin/env python3
"""Deploy V2 stack to remote server."""

import sys
import time
import paramiko

HOST = "47.94.210.217"
PASSWORD = "Lhw207905"
PROJECT = "/opt/AI-Companion-OS"


def run(client, cmd, timeout=1800):
    print(f"\n>>> {cmd}")
    sys.stdout.flush()
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    text = (out + err).strip()
    if text:
        print(text[-5000:])
    print(f"[exit: {code}]")
    sys.stdout.flush()
    return code, text


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=PASSWORD, timeout=30)
    print("Connected as root")

    run(client, "git config --global --add safe.directory /opt/AI-Companion-OS")
    for _ in range(3):
        code, _ = run(client, f"cd {PROJECT} && git fetch origin && git reset --hard origin/main")
        if code == 0:
            break
        time.sleep(5)

    run(client, f"cd {PROJECT} && docker compose down --remove-orphans || true")
    run(
        client,
        f"cd {PROJECT} && RESET_WORLD_ON_START=true docker compose build && "
        f"RESET_WORLD_ON_START=true docker compose up -d",
        timeout=2400,
    )

    print("\nWaiting 40s for services...")
    time.sleep(40)

    run(client, f"cd {PROJECT} && docker compose ps -a")
    run(client, "curl -s http://127.0.0.1/api/health || echo WEB_FAIL")
    run(client, "curl -s -o /dev/null -w 'web_root=%{http_code}\\n' http://127.0.0.1/")
    run(client, f"cd {PROJECT} && docker compose logs --tail=25 api")
    client.close()


if __name__ == "__main__":
    main()
