---
title: Docker Desktop WSL2 to Windows host networking: `host.docker.internal` can be un
tags: [docker, wsl2, networking, ollama, host-gateway]
created: 2026-03-29
source: Oracle Learn
project: github.com/soul-brews-studio/oracle-studio
---

# Docker Desktop WSL2 to Windows host networking: `host.docker.internal` can be un

Docker Desktop WSL2 to Windows host networking: `host.docker.internal` can be unreliable. Use `extra_hosts: - "host.docker.internal:host-gateway"` in docker-compose.yml for consistent connectivity to services like Ollama running on Windows. Prerequisites: set OLLAMA_HOST=0.0.0.0 on Windows and restart Ollama.

---
*Added via Oracle Learn*
