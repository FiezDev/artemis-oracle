# Jira Fetch - Design Specification

> Export Jira issues with configurable field mappings to Excel and CSV

**Created**: 2026-03-31
**Status**: Draft
**Author**: Artemis Oracle

---

## Overview

Jira Fetch is a web application that connects to Jira, syncs issues to TimescaleDB, and exports them to Excel or CSV with custom field mappings.

### Key Features

- Connect to Jira with API token (per-session auth)
- Full project sync with configurable JQL filters
- Visual field mapping editor (drag-drop)
- Export to Excel (.xlsx) and CSV
- Sync history and status tracking

---

## Architecture

```
jira-fetch/
├── apps/
│   ├── web/                 # React + TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/  # UI components
│   │   │   ├── pages/       # Route pages
│   │   │   ├── hooks/       # Custom React hooks
│   │   │   └── stores/      # State management (Zustand)
│   │   └── package.json
│   └── api/                 # Bun + Hono backend
│       ├── src/
│       │   ├── routes/      # API endpoints
│       │   ├── services/    # Business logic
│       │   ├── db/          # TimescaleDB queries
│       │   └── jira/        # Jira API client
│       └── package.json
├── packages/
│   └── shared/              # Shared types and utilities
│       ├── src/
│       │   ├── types/       # TypeScript interfaces
│       │   └── mappings/    # Field mapping schemas
│       └── package.json
├── docker-compose.yml       # TimescaleDB service
└── package.json             # Root workspace config
```

### Data Flow

1. User enters Jira credentials (API token) → stored in browser localStorage
2. Frontend calls API with credentials in headers
3. API fetches from Jira, stores in TimescaleDB, returns data
4. Field mappings configured via GUI, stored in DB
5. Export generates Excel/CSV from stored data

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS |
| State | Zustand + TanStack Query |
| Backend | Bun + Hono |
| Database | TimescaleDB (PostgreSQL extension) |
| Export | xlsx (Excel), csv-writer (CSV) |
| Validation | Zod |
| Drag-Drop | @dnd-kit/core |

---

## Database Schema

### Issues Table

```sql
CREATE TABLE issues (
  id BIGSERIAL,
  issue_key VARCHAR(50) NOT NULL,
  project_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(255) NOT NULL,

  -- Core fields (commonly queried)
  summary TEXT,
  status VARCHAR(100),
  priority VARCHAR(50),
  issue_type VARCHAR(50),
  assignee VARCHAR(255),
  reporter VARCHAR(255),
  created TIMESTAMPTZ,
  updated TIMESTAMPTZ,
  due_date DATE,

  -- Full raw data (all fields stored here)
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
  mappings JSONB NOT NULL,
  field_order TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(jira_instance_url, name)
);
```

### Sync Configurations Table

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

### Sync Logs Table

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

### Jira Connection

```
POST /api/jira/connect
Headers: X-Jira-URL, X-Jira-Email, X-Jira-Token
Response: { success: true, user: { displayName, emailAddress } }

GET /api/jira/projects
Headers: X-Jira-URL, X-Jira-Email, X-Jira-Token
Response: { projects: [{ key, name, lead, ... }] }

POST /api/jira/search
Headers: X-Jira-URL, X-Jira-Email, X-Jira-Token
Body: { jql: string, fields?: string[] }
Response: { issues: [...], total: number }
```

### Sync Management

```
GET /api/sync/configs
POST /api/sync/configs
PUT /api/sync/configs/:id
DELETE /api/sync/configs/:id
POST /api/sync/run/:id
GET /api/sync/status/:id
GET /api/sync/logs
```

### Field Mappings

```
GET /api/mappings
POST /api/mappings
PUT /api/mappings/:id
DELETE /api/mappings/:id
GET /api/mappings/fields
```

### Issues

```
GET /api/issues
Query: projectKey, status, assignee, startDate, endDate, limit, offset
Response: { issues: [...], total: number }

GET /api/issues/:key
Response: { issue: {...} }
```

### Export

```
POST /api/export/excel
POST /api/export/csv
Body: {
  mappingId: number,
  projectKey?: string,
  jql?: string,
  dateRange?: { start: string, end: string }
}
Response: Binary file download
```

---

## Frontend Structure

```
apps/web/src/
├── pages/
│   ├── Dashboard.tsx
│   ├── Connect.tsx
│   ├── Projects.tsx
│   ├── FieldMapping.tsx
│   ├── Issues.tsx
│   └── Export.tsx
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   ├── mapping/
│   │   ├── MappingEditor.tsx
│   │   ├── FieldList.tsx
│   │   ├── MappingPreview.tsx
│   │   └── MappingSave.tsx
│   ├── sync/
│   │   ├── SyncConfigForm.tsx
│   │   ├── SyncStatus.tsx
│   │   └── SyncHistory.tsx
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
│   └── useAppStore.ts
│
└── lib/
    ├── api.ts
    └── types.ts
```

### Page Descriptions

| Page | Purpose |
|------|---------|
| Dashboard | Overview: recent syncs, quick actions |
| Connect | Jira credentials input form |
| Projects | Project list & sync configuration |
| FieldMapping | Visual field mapping editor |
| Issues | Browse stored issues with filters |
| Export | Export configuration & download |

---

## Jira Fields to Support

The system must handle these Jira fields (70+ total):

**Standard Fields:**
- Summary, Issue key, Issue id, Issue Type, Status
- Project key, Project name, Project type, Project lead
- Priority, Resolution, Assignee, Reporter, Creator
- Created, Updated, Last Viewed, Resolved, Due date
- Votes, Labels, Description, Environment
- Original estimate, Remaining Estimate, Time Spent, Work Ratio
- Security Level, Attachment, Comment, Parent

**Custom Fields:**
- Epic fields (Color, Name, Status)
- Story Points, Story point estimate
- Team (Id, Name)
- Start date, Target start/end, Actual start/end
- Sprint-related fields
- Change management fields (reason, risk, type)
- Request Type, Satisfaction rating
- Development, Linked items
- And many more...

All fields stored in `raw_fields JSONB` for flexibility.

---

## Error Handling

| Scenario | Status | Response |
|----------|--------|----------|
| Invalid Jira credentials | 401 | `{error: "Invalid credentials"}` |
| Jira rate limit | 429 | `{retryAfter: 60}` |
| Sync in progress | 409 | `{syncId: "..."}` |
| Export too large | 413 | `{maxIssues: 10000}` |
| DB connection error | 503 | `{error: "Database unavailable"}` |

---

## Implementation Phases

| Phase | Scope |
|-------|-------|
| 1 | Core API: connect, search, store issues |
| 2 | Database sync jobs with scheduling |
| 3 | Field mapping UI with drag-drop |
| 4 | Export generation (Excel/CSV) |
| 5 | Polish, error handling, testing |

---

## Docker Compose

```yaml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: jira_fetch
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: jira_fetch
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data

  api:
    build: ./apps/api
    ports:
      - "3001:3001"
    environment:
      DATABASE_URL: postgres://jira_fetch:${DB_PASSWORD}@timescaledb:5432/jira_fetch
    depends_on:
      - timescaledb

  web:
    build: ./apps/web
    ports:
      - "3000:3000"
    depends_on:
      - api

volumes:
  timescale_data:
```

---

## Success Criteria

1. User can connect to Jira instance with API token
2. User can sync projects with custom JQL filters
3. User can create and save field mappings via drag-drop UI
4. User can export issues to Excel and CSV with mapped fields
5. Sync history is tracked and viewable
6. System handles 10,000+ issues without performance degradation
