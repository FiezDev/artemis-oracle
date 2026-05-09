---
title: Arra Oracle + TaskNet Agent Reference Guide
tags: [arra-oracle, tasknet, api, reference, agent-guide, openclaw, qone-corp]
created: 2026-04-07
source: Integration Test
project: github.com/fiezdev/artemis-oracle
---

## Arra Oracle MCP (Port 47778)
All agents use these MCP tools with `arra_` prefix:
- **arra_search(query, limit, mode)** — Hybrid FTS+vector search across Oracle knowledge. Modes: hybrid, fts, vector.
- **arra_read(id or file)** — Read full document by ID or file path.
- **arra_list(type, limit)** — List documents filtered by type (learning, principle, retro).
- **arra_concepts(limit)** — Browse concept tags in knowledge base.
- **arra_learn(pattern, concepts, project)** — Add new knowledge. Use concepts array for tagging.
- **arra_stats()** — Get knowledge base health stats.
- **arra_thread(message, title)** — Create/continue forum threads for multi-turn consultation.
- **arra_threads(status, limit)** — List forum threads.
- **arra_thread_read(threadId)** — Read thread messages.
- **arra_trace(query, scope, project, foundFiles)** — Log discovery sessions with dig points.
- **arra_trace_list(limit)** — List past traces.
- **arra_handoff(content, slug)** — Save session context for future sessions.
- **arra_inbox(limit)** — Read pending handoffs.
- **arra_supersede(oldId, newId, reason)** — Mark old docs as outdated.

## Arra Oracle REST API (Port 47779)
Fallback when MCP unavailable:
- GET /api/health, /api/stats, /api/search?q=, /api/list, /api/inbox
- POST /api/learn, /api/handoff, /api/traces, /api/forum/threads

## TaskNet REST API (Port 5501)
Multi-agent task coordination. All mutations require X-Agent-ID header.

**Authentication**: X-Agent-ID header with agent name (artemis, forge, pixel, etc.)

**Task Lifecycle**: available → in_progress → in_review → done (or blocked)

**Endpoints**:
- GET /api/v1/tasks — List tasks (filters: sprint_id, status, agent, priority)
- GET /api/v1/tasks/:id — Get task with assignments
- POST /api/v1/tasks — Create task (requires X-Agent-ID)
- PATCH /api/v1/tasks/:id — Update task
- POST /api/v1/tasks/:id/claim — Agent claims task
- POST /api/v1/tasks/:id/release — Agent releases task
- POST /api/v1/tasks/:id/complete — Agent completes task
- POST /api/v1/tasks/:id/block — Report blocker
- POST /api/v1/tasks/:id/unblock — Resolve blocker
- GET /api/v1/agents — List all agents
- GET /api/v1/agents/:id — Get agent details
- PATCH /api/v1/agents/:id — Update agent status
- POST /api/v1/agents/:id/heartbeat — Send heartbeat
- GET /api/v1/sprints/current — Current sprint with stats
- GET /api/v1/blockers — List blockers
- GET /api/v1/dependencies — List dependency edges
- GET /api/v1/workflows — List workflow templates
- POST /api/v1/workflows/:id/run — Trigger workflow
- GET /api/v1/health — Health check
- GET /api/v1/stats — Aggregate stats

## The 20-Agent Workforce
| Division | Lead | Agents |
|----------|------|--------|
| Atlas (Developer) | atlas | forge, pixel, shield, deploy |
| Iris (TikTok) | iris | luna, sage, vox, nova, reel |
| Herald (Facebook) | herald | echo, pulse |
| Axiom (Improvement) | axiom | prism, spark, metric |
| Cross-cutting | artemis | flux (coordinator) |

## Integration Test Results (2026-04-07)
- All MCP tools: PASS (search, read, list, concepts, threads, traces)
- REST API: PASS (health, stats, search, list)
- TaskNet: PASS (health, stats, agents, tasks, sprints, blockers, dependencies, workflows, heartbeat)
- Known bugs: vector search low coverage (130/177), handoff EROFS (Docker :ro mounts), task creation fails (missing ID default)
