# Jira Fetch — Field Mapping Export System

**Created:** 2026-03-31
**Status:** Approved for Implementation
**Author:** Artemis Oracle

---

## Overview

A web-based system to export Jira issues with customizable field mappings. Supports Excel (.xlsx) and CSV export formats, stores data in TimescaleDB for historical queries, and provides a GUI for configuring field mappings.

## Core Requirements

| Aspect | Decision |
|--------|----------|
| Export formats | Excel (.xlsx) + CSV |
| Storage | TimescaleDB (existing Docker) |
| Field mapping | GUI/Web interface |
| Frontend | React + TypeScript |
| Backend | Bun + Hono |
| Auth | API token per session (localStorage) |
| Data scope | Full project sync with configurable filters |

## Jira Fields to Support

The system must handle 70+ fields including:

**Standard Fields:**
- Summary, Issue key, Issue id, Issue Type, Status
- Project key, Project name, Project type, Project lead
- Priority, Resolution, Assignee, Reporter, Creator
- Created, Updated, Last Viewed, Resolved, Due date
- Votes, Labels, Description, Environment
- Original estimate, Remaining Estimate, Time Spent, Work Ratio

**Aggregated Fields:**
- Σ Original Estimate, Σ Remaining Estimate, Σ Time Spent

**Links & Relationships:**
- Inward/Outward issue links (Blocks, etc.)
- Parent, Parent key, Parent summary
- Attachments

**Custom Fields:**
- Story Points, Story point estimate
- Team Id, Team Name
- Epic Name, Epic Color, Epic Status
- Start date, Target start, Target end, Actual start, Actual end
- Rank, Request Type, Satisfaction rating
- Category, Change reason, Change risk, Change type
- Development, Insights, Focus Areas, Goals
- And 30+ additional custom fields

**Comments:** Multiple comments per issue

---

## Architecture

### Project Structure (Monorepo)

```
jira-fetch/
├── apps/
│   ├── web/                    # React + TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   ├── hooks/
│   │   │   ├── stores/
│   │   │   └── lib/
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── api/                    # Bun + Hono backend
│       ├── src/
│       │   ├── routes/
│       │   ├── services/
│       │   ├── db/
│       │   └── jira/
│       └── package.json
├── packages/
│   └── shared/                 # Shared types and utilities
│       ├── src/
│       │   ├── types/
│       │   └── mappings/
│       └── package.json
├── docker-compose.yml
└── package.json                # Root workspace config
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────┐  ┌─────────────┐  ┌───────────┐  ┌────────────┐  │
│  │ Connect  │→ │ Field Map   │→ │ Sync Config│→ │   Export   │  │
│  │  Page    │  │   Editor    │  │   Setup    │  │   Page     │  │
│  └────┬─────┘  └──────┬──────┘  └─────┬──────┘  └─────┬──────┘  │
└───────┼───────────────┼───────────────┼───────────────┼─────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API (Hono)                               │
│  ┌──────────┐  ┌─────────────┐  ┌───────────┐  ┌────────────┐  │
│  │ /connect │  │ /mappings   │  │  /sync    │  │  /export   │  │
│  └────┬─────┘  └──────┬──────┘  └─────┬──────┘  └─────┬──────┘  │
└───────┼───────────────┼───────────────┼───────────────┼─────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TimescaleDB                                 │
│  ┌──────────┐  ┌─────────────┐  ┌───────────┐  ┌────────────┐  │
│  │ issues   │  │field_mappings│  │sync_configs│  │ sync_logs │  │
│  └──────────┘  └─────────────┘  └───────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Jira Cloud API                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Token Storage Trade-off

**Decision:** API tokens stored in browser `localStorage` and passed via headers.

**Risks acknowledged:**
- Vulnerable to XSS attacks — any malicious script can read localStorage
- Token visible in browser dev tools
- Token passed on every request

**Mitigations:**
- Content-Security-Policy (CSP) headers on all responses
- HttpOnly cookies NOT used (would require backend token storage)
- Session-scoped: token only valid during browser session
- No server-side token persistence

**Alternative considered (rejected for this use case):**
- OAuth flow with server-side token storage — adds complexity, requires Jira app registration
- Session-based auth with server-side token encryption — requires stateful server

This trade-off is acceptable for single-user or trusted-team deployments. Not recommended for public-facing applications.

---

---

## Sync Strategy

### Pagination

Jira API returns max 100 issues per page. For large projects:

- **Batch size:** 100 issues per request
- **Parallel requests:** 3 concurrent (stays under rate limit)
- **Progress tracking:** Store `issues_synced` count in sync_logs

**Example:** 10,000-issue project = 100 API calls ≈ 2-3 minutes

### Incremental Sync

| Sync Type | JQL Filter | Use Case |
|-----------|------------|----------|
| Full | `project = PROJ` | Initial sync |
| Incremental | `project = PROJ AND updated > "{last_sync}"` | Subsequent syncs |

**Logic:**
1. First sync: Full fetch, all issues marked as "new"
2. Subsequent syncs: Only fetch issues updated since `last_sync_at`
3. Compare `issue_key + updated` to detect changes
4. Insert new version if changed, otherwise skip

**Orphaned Issues:** Not deleted. TimescaleDB keeps history. Use `synced_at` to query latest version.

### Concurrent Sync Handling

- **Lock per config:** Only one sync per `sync_config_id` at a time
- **Timeout:** 30 minutes max (for very large projects)
- **Crash recovery:** Syncs that don't complete within 30min marked as "failed"
- **Queue behavior:** New sync requests while one running → return 409 with `syncId` of running sync

### Rate Limit Handling

Jira Cloud rate limit: ~1000 requests/minute per user.

**Strategy:**
- Max 10 requests/second (600/minute) — safe margin
- On 429: Exponential backoff (1s, 2s, 4s, max 30s)
- Max 5 retries per request before failing

---

## Field Discovery

### GET `/api/mappings/fields`

Returns all available fields from Jira for the connected instance.

**Implementation:**
1. Call Jira REST API `/rest/api/3/field`
2. Parse response to extract field metadata
3. Return structured list

**Response:**
```json
{
  "standard": [
    { "id": "summary", "name": "Summary", "type": "string" },
    { "id": "status", "name": "Status", "type": "object" },
    { "id": "priority", "name": "Priority", "type": "object" }
  ],
  "custom": [
    { "id": "customfield_10016", "name": "Story Points", "type": "number" },
    { "id": "customfield_10014", "name": "Epic Name", "type": "string" }
  ]
}
```

**Custom field identification:** By field ID (e.g., `customfield_10016`) — more stable than name. Display name to user, store ID in mapping.

**Renamed fields:** If custom field renamed in Jira, mapping still works (ID unchanged). UI shows warning if field name mismatch detected.

---

## Mapping Scope

**Mappings are per-Jira-instance:**
- `jira_instance_url` in `field_mappings` table
- Same tool can manage multiple Jira instances
- Mappings do NOT transfer between instances (field IDs differ)

**User scope:** Single-user tool in this version. Multi-user would require:
- `user_id` column in all tables
- Per-user credential encryption
- Row-level security

---

## Database Schema

### Issues Table (Hypertable)

```sql
CREATE TABLE issues (
  id BIGSERIAL,
  issue_key VARCHAR(50) NOT NULL,
  project_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(255) NOT NULL,

  -- Core fields (extracted for queries)
  summary TEXT,
  status VARCHAR(100),
  priority VARCHAR(50),
  issue_type VARCHAR(50),
  assignee VARCHAR(255),
  reporter VARCHAR(255),
  created TIMESTAMPTZ,
  updated TIMESTAMPTZ,
  due_date DATE,

  -- Full raw data (all 70+ fields)
  raw_fields JSONB NOT NULL,

  synced_at TIMESTAMPTZ DEFAULT NOW(),

  -- Primary key allows same issue at multiple sync times (history tracking)
  PRIMARY KEY (jira_instance_url, issue_key, synced_at)
);

-- Prevent duplicate issues within same sync run
CREATE UNIQUE INDEX idx_issues_unique ON issues(jira_instance_url, issue_key)
  WHERE synced_at = (SELECT MAX(synced_at) FROM issues i2 WHERE i2.issue_key = issues.issue_key);

SELECT create_hypertable('issues', 'synced_at');

CREATE INDEX idx_issues_project ON issues(project_key);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_assignee ON issues(assignee);
CREATE INDEX idx_issues_updated ON issues(updated);
```

### Field Mappings Table

```sql
CREATE TABLE field_mappings (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  jira_instance_url VARCHAR(255) NOT NULL,

  -- Mapping: {"Jira Field Name": "Export Column Name"}
  mappings JSONB NOT NULL,

  -- Which fields to include (order matters for export)
  field_order TEXT[] NOT NULL DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(jira_instance_url, name)
);
```

### Sync Configs Table

```sql
CREATE TABLE sync_configs (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  jira_instance_url VARCHAR(255) NOT NULL,
  project_keys TEXT[] NOT NULL,
  jql_filter TEXT,
  include_fields TEXT[] DEFAULT '{}',
  sync_interval_hours INTEGER DEFAULT 24,
  last_sync_at TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Sync Logs Table (Hypertable)

```sql
CREATE TABLE sync_logs (
  id BIGSERIAL,
  jira_instance_url VARCHAR(255) NOT NULL,
  sync_config_id INTEGER REFERENCES sync_configs(id),
  project_key VARCHAR(50),
  jql_used TEXT,
  issues_synced INTEGER,
  issues_updated INTEGER,
  issues_new INTEGER,
  sync_started TIMESTAMPTZ,
  sync_completed TIMESTAMPTZ,
  status VARCHAR(20),
  error_message TEXT,
  PRIMARY KEY (jira_instance_url, id, sync_started)
);

SELECT create_hypertable('sync_logs', 'sync_started');
```

---

## API Endpoints

### Authentication

All endpoints require headers:
```
X-Jira-URL: https://yourcompany.atlassian.net
X-Jira-Email: user@company.com
X-Jira-Token: <API_TOKEN>
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jira/connect` | Validate Jira credentials |
| GET | `/api/jira/projects` | List available projects |
| POST | `/api/jira/search` | Execute JQL query |
| GET | `/api/sync/configs` | List sync configurations |
| POST | `/api/sync/configs` | Create sync config |
| PUT | `/api/sync/configs/:id` | Update sync config |
| DELETE | `/api/sync/configs/:id` | Delete sync config |
| POST | `/api/sync/run/:id` | Trigger manual sync |
| GET | `/api/sync/status/:id` | Get sync status |
| GET | `/api/sync/logs` | List all sync logs |
| GET | `/api/mappings` | List field mappings |
| POST | `/api/mappings` | Create field mapping |
| PUT | `/api/mappings/:id` | Update field mapping |
| DELETE | `/api/mappings/:id` | Delete field mapping |
| GET | `/api/mappings/fields` | Get available Jira fields |
| GET | `/api/issues` | List stored issues |
| GET | `/api/issues/:key` | Get single issue |
| POST | `/api/export/excel` | Export to Excel |
| POST | `/api/export/csv` | Export to CSV |

### Export Request Body

```json
{
  "mappingId": 1,
  "projectKey": "PROJ",
  "jql": "status = Done AND updated > -30d",
  "dateRange": {
    "start": "2026-01-01",
    "end": "2026-03-31"
  }
}
```

---

## Frontend Structure

```
apps/web/src/
├── pages/
│   ├── Dashboard.tsx           # Overview: recent syncs, quick actions
│   ├── Connect.tsx             # Jira credentials input form
│   ├── Projects.tsx            # Project list & sync configuration
│   ├── FieldMapping.tsx        # Visual field mapping editor
│   ├── Issues.tsx              # Browse stored issues with filters
│   └── Export.tsx              # Export configuration & download
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   │
│   ├── mapping/
│   │   ├── MappingEditor.tsx   # Drag-drop field mapping
│   │   ├── FieldList.tsx       # Available Jira fields
│   │   ├── MappingPreview.tsx  # Preview table
│   │   └── MappingSave.tsx     # Save modal
│   │
│   ├── sync/
│   │   ├── SyncConfigForm.tsx
│   │   ├── SyncStatus.tsx
│   │   └── SyncHistory.tsx
│   │
│   └── export/
│       ├── ExportForm.tsx
│       └── ExportPreview.tsx
│
├── hooks/
│   ├── useJiraAuth.ts
│   ├── useProjects.ts
│   ├── useSync.ts
│   └── useExport.ts
│
├── stores/
│   └── useAppStore.ts          # Zustand store
│
└── lib/
    ├── api.ts
    └── types.ts
```

### Key UI Features

1. **Connect Page** — Enter Jira URL, email, API token → validates and stores in localStorage
2. **Field Mapping** — Two-panel drag-drop interface with live preview
3. **Projects/Sync** — Configure which projects to sync with JQL filters
4. **Export** — Select mapping, filters, download Excel or CSV

---

## Dependencies

### Backend

```json
{
  "hono": "^4.x",
  "postgres": "^3.x",
  "xlsx": "^0.x",
  "csv-writer": "^1.x",
  "zod": "^3.x"
}
```

**Note:** Using `postgres` driver directly for TimescaleDB (PostgreSQL extension). NOT using libSQL.

### Frontend

```json
{
  "react": "^18.x",
  "react-router-dom": "^6.x",
  "@tanstack/react-query": "^5.x",
  "zustand": "^4.x",
  "tailwindcss": "^3.x",
  "@dnd-kit/core": "^6.x",
  "lucide-react": "^0.x",
  "xlsx": "^0.x"
}
```

---

## Error Handling

| Scenario | HTTP Code | Response Body | Frontend Behavior |
|----------|-----------|---------------|-------------------|
| Invalid credentials | 401 | `{error: "Invalid credentials"}` | Show error, clear stored creds |
| Jira rate limit | 429 | `{retryAfter: 60}` | Auto-retry with exponential backoff |
| Sync in progress | 409 | `{syncId: "...", estimatedTime: 120}` | Poll status endpoint |
| Export too large | 413 | `{maxIssues: 10000, suggestion: "Add date filter"}` | Show filter suggestion |
| DB unavailable | 503 | `{error: "Database unavailable"}` | Show error, retry button |
| Network timeout | 504 | `{error: "Jira API timeout"}` | Retry with longer timeout |
| Field not found | 400 | `{field: "customfield_10016", error: "Field not found"}` | Show warning in mapping UI |

### Loading States

All async operations show:
- Spinner during operation
- Progress bar for long operations (sync, export)
- Skeleton loaders for initial page loads

### Error Messages

User-friendly error messages (not raw API errors):
- "Could not connect to Jira. Check your URL and API token."
- "Export is too large. Try adding a date range filter."
- "Sync took too long and was cancelled. Try a smaller project."

---

## Implementation Phases

| Phase | Focus | Duration |
|-------|-------|----------|
| 1 | Core API (connect, search, store) | 2-3 days |
| 2 | Database sync jobs | 2-3 days |
| 3 | Field mapping UI | 3-4 days |
| 4 | Export generation (Excel/CSV) | 2 days |
| 5 | Polish & error handling | 1-2 days |

**Total:** ~10-14 days

---

## Success Criteria

- [ ] Can connect to Jira Cloud with API token (validated before proceeding)
- [ ] Can sync all issues from configured projects with pagination
- [ ] Incremental syncs only fetch changed issues
- [ ] Can create/edit/delete field mappings via drag-drop GUI
- [ ] Can export synced issues to Excel with mapped fields
- [ ] Can export synced issues to CSV with mapped fields
- [ ] Field mappings persist across sessions (per Jira instance)
- [ ] Sync history is trackable with status, counts, timestamps
- [ ] Error messages are clear and actionable
- [ ] Loading states shown for all async operations
- [ ] Rate limits handled gracefully with retry
