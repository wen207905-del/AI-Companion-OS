#!/usr/bin/env python3
"""Diagnose and fix 502 on server."""
import paramiko
import time

HOST = "47.94.210.217"
PASSWORD = "Lhw207905"
PROJECT = "/opt/AI-Companion-OS"


def run(client, cmd, timeout=120):
    print(f"\n>>> {cmd[:120]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    text = (out + err).strip()
    if text:
        print(text[-4000:])
    print(f"[exit: {code}]")
    return code, text


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=PASSWORD, timeout=30)
    sudo = f"echo '{PASSWORD}' | sudo -S"

    run(client, f"cd {PROJECT} && docker compose ps -a")
    run(client, f"cd {PROJECT} && docker compose logs --tail=40 web")
    run(client, f"cd {PROJECT} && docker compose logs --tail=40 api")
    run(client, "curl -sv http://127.0.0.1/api/health 2>&1 | tail -30")
    run(client, "curl -sv http://127.0.0.1/ 2>&1 | tail -20")
    run(client, f"cd {PROJECT} && docker compose exec -T web wget -qO- http://api:8000/api/health 2>&1 | head -c 400")
    run(client, "ss -tlnp | grep ':80 '")
    run(client, f"cd {PROJECT} && docker compose exec -T web cat /etc/nginx/conf.d/default.conf")

    # fix git permissions for admin
    run(client, f"{sudo} chown -R admin:admin {PROJECT}")

    # restart stack cleanly
    run(client, f"cd {PROJECT} && docker compose down && docker compose up -d", timeout=300)
    time.sleep(25)
    run(client, f"cd {PROJECT} && docker compose ps")
    run(client, "curl -s http://127.0.0.1/api/health")
    run(client, "curl -sI http://127.0.0.1/ | head -10")

    client.close()


if __name__ == "__main__":
    main()
