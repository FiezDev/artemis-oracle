# Jira Fetch — Design Specification

> Export Jira issues with customizable field mappings to Excel and CSV

**Created:** 2026-03-31
**Author:** Artemis Oracle
**Status:** Approved

---

## Overview

Jira Fetch is a full-stack web application that syncs Jira issues to TimescaleDB and exports them to Excel or CSV with user-defined field mappings through a visual interface.

---

## Requirements Summary

| Aspect | Decision |
|--------|----------|
| Export formats | Excel (.xlsx) + CSV |
| Storage | TimescaleDB (existing Docker) |
| Field mapping | GUI/Web interface |
| Frontend | React + TypeScript |
| Backend | Bun + Hono |
| Auth | API token per session (localStorage) |
| Data scope | Full project sync with configurable filters |

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

## Database Schema (TimescaleDB)

```sql
-- Hypertable for Jira issues
CREATE TABLE issues (
  id BIGSERIAL,
  issue_key VARCHAR(50) NOT NULL,
  project_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(255) NOT NULL,

  -- Core fields (commonly queried, extracted from raw)
  summary TEXT,
  status VARCHAR(100),
  priority VARCHAR(50),
  issue_type VARCHAR(50),
  assignee VARCHAR(255),
  reporter VARCHAR(255),
  created TIMESTAMPTZ,
  updated TIMESTAMPTZ,
  due_date DATE,

  -- Full raw data (all 70+ fields stored here)
  raw_fields JSONB NOT NULL,

  synced_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jira_instance_url, issue_key, synced_at)
);

SELECT create_hypertable('issues', 'synced_at');

-- Indexes for common queries
CREATE INDEX idx_issues_project ON issues(project_key);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_assignee ON issues(assignee);

-- Field mapping configurations
CREATE TABLE field_mappings (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  jira_instance_url VARCHAR(255) NOT NULL,

  -- Mapping: {"Jira Field Name": "Export Column Name", ...}
  mappings JSONB NOT NULL,

  -- Which fields to include in export (order matters)
  field_order TEXT[] NOT NULL DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(jira_instance_url, name)
);

-- Sync configurations (for project sync)
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

-- Sync history logs
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

### Jira Fields to Capture

The following fields are downloaded from Jira and stored in `raw_fields`:

**Standard Fields:**
- Summary, Issue key, Issue id, Issue Type, Status
- Project key, Project name, Project type, Project lead, Project lead id, Project description
- Priority, Resolution
- Assignee, Assignee Id, Reporter, Reporter Id, Creator, Creator Id
- Created, Updated, Last Viewed, Resolved, Due date
- Votes, Labels, Description, Environment
- Original estimate, Remaining Estimate, Time Spent, Work Ratio
- Σ Original Estimate, Σ Remaining Estimate, Σ Time Spent
- Security Level
- Inward/Outward issue links (Blocks)
- Attachments
- Comments
- Parent, Parent key, Parent summary
- Status Category, Status Category Changed

**Custom Fields:**
- Actual end, Actual start, Approvals
- Atlassian project, Atlassian project status
- Category, Change reason, Change risk, Change type
- Comments, Delivery progress, Delivery status
- Development, Epic Color, Epic Name, Epic Status
- Focus Areas, Goals
- Idea archived, Idea archived on
- Impact, Insights, Issue color
- Linked items, Locked forms, Open forms
- Project overview key, Project overview status
- Rank, Request Type, Request participants
- Satisfaction rating, Satisfaction date
- Sentiment, Start date
- Story Points, Story point estimate
- Submitted forms, Target end, Target start
- Team Id, Team Name
- Total forms, Vulnerability, Work category
- [CHART] Date of First Response, [CHART] Time in Status

---

## API Endpoints

### Jira Connection
```
POST   /api/jira/connect              # Validate Jira credentials
GET    /api/jira/projects             # List available projects
POST   /api/jira/search               # Execute JQL query, return results
```

### Sync Management
```
GET    /api/sync/configs              # List sync configurations
POST   /api/sync/configs              # Create sync config
PUT    /api/sync/configs/:id          # Update sync config
DELETE /api/sync/configs/:id          # Delete sync config
POST   /api/sync/run/:id              # Trigger manual sync
GET    /api/sync/status/:id           # Get sync status/history
GET    /api/sync/logs                 # List all sync logs
```

### Field Mappings
```
GET    /api/mappings                  # List field mappings
POST   /api/mappings                  # Create field mapping
PUT    /api/mappings/:id              # Update field mapping
DELETE /api/mappings/:id              # Delete field mapping
GET    /api/mappings/fields           # Get available Jira fields (for UI dropdown)
```

### Issues
```
GET    /api/issues                    # List stored issues (with filters)
GET    /api/issues/:key               # Get single issue details
```

### Export
```
POST   /api/export/excel              # Export to Excel (.xlsx)
POST   /api/export/csv                # Export to CSV
```

### Authentication Pattern

All endpoints expect headers:
```
X-Jira-URL: https://yourcompany.atlassian.net
X-Jira-Email: user@company.com
X-Jira-Token: <API_TOKEN>
```

### Export Request Body

```json
{
  "mappingId": 1,
  "projectKey": "PROJ",
  "jql": "status = Done AND updated > -30d",
  "dateRange": { "start": "2026-01-01", "end": "2026-03-31" }
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
│   │   ├── Sidebar.tsx         # Navigation
│   │   └── Header.tsx          # User info, connection status
│   │
│   ├── mapping/
│   │   ├── MappingEditor.tsx   # Drag-drop field mapping
│   │   ├── FieldList.tsx       # Available Jira fields (left panel)
│   │   ├── MappingPreview.tsx  # Preview table with mapped data
│   │   └── MappingSave.tsx     # Save/update mapping modal
│   │
│   ├── sync/
│   │   ├── SyncConfigForm.tsx  # Create/edit sync config
│   │   ├── SyncStatus.tsx      # Progress indicator
│   │   └── SyncHistory.tsx     # Table of past syncs
│   │
│   └── export/
│       ├── ExportForm.tsx      # Format, mapping, filters
│       └── ExportPreview.tsx   # Data preview before download
│
├── hooks/
│   ├── useJiraAuth.ts          # Manage credentials in localStorage
│   ├── useProjects.ts          # Fetch project list
│   ├── useSync.ts              # Sync operations
│   └── useExport.ts            # Export operations
│
├── stores/
│   └── useAppStore.ts          # Zustand store (connection, UI state)
│
└── lib/
    ├── api.ts                  # API client (fetch wrapper)
    └── types.ts                # Shared TypeScript types
```

### Key UI Features

1. **Connect Page** — Enter Jira URL, email, API token → validates and stores in localStorage
2. **Field Mapping** — Two-panel interface:
   - Left: Available Jira fields (draggable)
   - Right: Export columns (drop target)
   - Preview table shows live data with current mapping
3. **Projects/Sync** — Configure which projects to auto-sync, set JQL filters
4. **Export** — Select mapping, filters, choose Excel or CSV, download

---

## Technical Implementation

### Backend Dependencies

```json
{
  "dependencies": {
    "hono": "^4.x",
    "postgres": "^3.x",
    "xlsx": "^0.x",
    "csv-writer": "^1.x",
    "zod": "^3.x"
  },
  "devDependencies": {
    "bun-types": "latest"
  }
}
```

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "react-router-dom": "^6.x",
    "@tanstack/react-query": "^5.x",
    "zustand": "^4.x",
    "tailwindcss": "^3.x",
    "@dnd-kit/core": "^6.x",
    "lucide-react": "^0.x",
    "xlsx": "^0.x"
  },
  "devDependencies": {
    "vite": "^5.x",
    "typescript": "^5.x"
  }
}
```

---

## Error Handling

| Scenario | Backend Response | Frontend Behavior |
|----------|------------------|-------------------|
| Invalid Jira credentials | 401 + `{error: "Invalid credentials"}` | Show login error, clear stored creds |
| Jira rate limit | 429 + `{retryAfter: 60}` | Show warning, auto-retry after delay |
| Sync in progress | 409 + `{syncId: "..."}` | Poll status, show progress |
| Export too large | 413 + `{maxIssues: 10000}` | Suggest date range filter |
| DB connection error | 503 + `{error: "Database unavailable"}` | Show error, retry button |

---

## Implementation Phases

| Phase | Scope | Duration |
|-------|-------|----------|
| 1 | Core API (connect, search, store) | - |
| 2 | Database sync jobs | - |
| 3 | Field mapping UI | - |
| 4 | Export generation (Excel/CSV) | - |
| 5 | Polish & error handling | - |

---

## Success Criteria

- [ ] User can connect to Jira with API token
- [ ] User can configure project sync with JQL filters
- [ ] User can create and save custom field mappings via drag-drop UI
- [ ] User can export synced issues to Excel (.xlsx) format
- [ ] User can export synced issues to CSV format
- [ ] All 70+ Jira fields are captured and available for mapping
- [ ] Data persists in TimescaleDB across sessions
