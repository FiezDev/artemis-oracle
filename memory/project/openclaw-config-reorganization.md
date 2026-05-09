---
name: OpenClaw Config Reorganization
description: Agent workspace paths and default agent changes
type: project
---

**Change:** OpenClaw agent workspace paths updated from `~/oracle/qone_corp/agents/` to `~/dev-personal/qone_corp/agents/`. Main agent removed, artemis is now default agent.

**Why:** User reorganization of development environment structure.
**How to apply:** Future references to agent workspaces should use the new path structure. Artemis is the primary agent for all OpenClaw operations.
