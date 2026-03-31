---
type: learning
concepts: [docker, wsl2, networking, ollama, host-gateway]
date: 2026-03-30
source: session: oracle-studio docker deployment
---

# Docker Desktop WSL2 to Windows Host Networking

When running Docker containers that need to reach services on the Windows host (like Ollama):

## Problem
`host.docker.internal` can be unreliable or resolve to incorrect IPs in Docker Desktop + WSL2 setups.

## Solution
Add to `docker-compose.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
  - "ollama:host-gateway"
environment:
  - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Prerequisites on Windows
1. Set Ollama to listen on all interfaces:
   ```powershell
   setx OLLAMA_HOST "0.0.0.0"
   ```
2. Restart Ollama application
3. Verify: `netstat -an | findstr 11434` should show `0.0.0.0:11434`
