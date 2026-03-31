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
  PRIMARY KEY (jira_instance_url, issue_key, synced_at)
);

SELECT create_hypertable('issues', 'synced_at');

CREATE INDEX idx_issues_project ON issues(project_key);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_assignee ON issues(assignee);
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
  "@libsql/client": "^0.x",
  "postgres": "^3.x",
  "xlsx": "^0.x",
  "csv-writer": "^1.x",
  "zod": "^3.x"
}
```

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

| Scenario | Response | Frontend |
|----------|----------|----------|
| Invalid credentials | 401 | Show error, clear creds |
| Jira rate limit | 429 + retryAfter | Auto-retry after delay |
| Sync in progress | 409 + syncId | Poll status |
| Export too large | 413 | Suggest date filter |
| DB unavailable | 503 | Show error, retry |

---

## Implementation Phases

1. **Phase 1** — Core API (connect, search, store)
2. **Phase 2** — Database sync jobs
3. **Phase 3** — Field mapping UI
4. **Phase 4** — Export generation (Excel/CSV)
5. **Phase 5** — Polish & error handling

---

## Success Criteria

- [ ] Can connect to Jira Cloud with API token
- [ ] Can sync all issues from configured projects
- [ ] Can create/edit/delete field mappings via GUI
- [ ] Can export synced issues to Excel with mapped fields
- [ ] Can export synced issues to CSV with mapped fields
- [ ] Field mappings persist across sessions
- [ ] Sync history is trackable
