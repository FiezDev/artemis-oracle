# RIC-159 + RIC-160 Implementation Plan

## Scope

11 modules across 2 Jira tickets. All code in `/home/bjgdr/dev-work/Rice-Guard-API`.

---

## Phase 1: DB Schema + Migrations

### 1a. New tables in `src/db/schema/index.ts`

**`deviceSyncStates`** (RIC-159 Module 2.5.1)
- id uuid PK, deviceId varchar(50) FK→iotDevices, lastSyncAt timestamp, expectedIntervalSeconds integer default 14400, missedWindows integer default 0, status enum(SYNCED/DELAYED/STALLED)

**`deviceConnectionEvents`** (RIC-159 Module 2.5.8)
- id uuid PK, deviceId varchar(50) FK→iotDevices, rssi integer, wifiSsid varchar(100), freeHeap integer, uptimeMs bigint, eventTimestamp timestamp defaultNow()

**`sensorSummaryReports`** (RIC-159 Module 2.5.10)
- id uuid PK, farmId uuid FK→farms, reportType enum(DAILY/WEEKLY), periodStart date, periodEnd date, summaryData jsonb, generatedAt timestamp defaultNow()

**`pestReports`** (RIC-160 Module 2.5.4)
- id uuid PK, farmId uuid FK→farms, generatedAt timestamp defaultNow(), severity enum(LOW/MEDIUM/HIGH/CRITICAL), pestTypes jsonb, affectedZones jsonb, sensorAnomalies jsonb, recommendations text, status enum(DRAFT/PUBLISHED/ARCHIVED) default 'DRAFT'

**`farmerProfiles`** (RIC-160 Module 2.5.2)
- id uuid PK, userId uuid FK→users unique, surveyId uuid FK→surveys nullable, displayName varchar(255), phone varchar(50), province varchar(100), farmAreaHectares numeric(10,2), riceVarieties jsonb, plantingMethods jsonb, lastSyncedAt timestamp, createdAt timestamp, updatedAt timestamp

Add relations for all new tables.

### 1b. Migration file: `drizzle/migrations/0016_ric159_ric160_tables.sql`
Single migration creating all 5 tables with FKs and indexes.

---

## Phase 2: RIC-159 Modules

### Module 2.5.1 — Sync Manager
- `src/infrastructure/cron/syncMonitorCron.ts` — Every 15 min, query deviceSyncStates where lastSyncAt < NOW() - expectedInterval, increment missedWindows, publish WARNING at 2, CRITICAL at 3+, update status SYNCED→DELAYED→STALLED
- `src/infrastructure/cron/index.ts` — Register exports
- `src/consumers/telemetry.consumer.ts` — After successful persist, upsert deviceSyncStates.lastSyncAt, reset missedWindows to 0

### Module 2.5.7 — Device Auth
- `src/infrastructure/rabbitmq/device-auth.ts` — DeviceAuthService: provisionDevice(deviceId, password), deprovisionDevice(deviceId), setTopicPermissions(deviceId). Uses RabbitMQ Management HTTP API via fetch to `RABBITMQ_MGMT_URL/api/users` and `/api/topic-permissions`
- `src/domains/device-auth/index.ts` — Barrel
- `src/domains/device-auth/model.ts` — ProvisionResult type
- `src/domains/device-auth/resolver.ts` — GraphQL mutations: provisionDevice, deprovisionDevice, rotateDeviceCredentials
- `src/graphql/schema.ts` — Add DeviceAuthResult type + mutations

### Module 2.5.8 — Connection Monitor
- `src/consumers/device-status.consumer.ts` — On heartbeat, INSERT into deviceConnectionEvents, compute RSSI trend (avg of last 5 vs current), publish WARNING if degradation > 15 dBm
- `src/infrastructure/cron/connectionMonitorCron.ts` — Hourly, clean up connection events older than 7 days

### Module 2.5.9 — Batch Upload
- `src/consumers/telemetry.consumer.ts` — Refactor: batch insert readings using Drizzle `db.insert().values([...])` instead of loop, add dedup by (sensorId, timestamp) via ON CONFLICT DO NOTHING

### Module 2.5.10 — Report Generator
- `src/infrastructure/cron/reportGeneratorCron.ts` — Daily at midnight (Asia/Bangkok), generate daily summaries per farm using TimescaleDB `time_bucket('1 day', timestamp)`, store in sensorSummaryReports. Weekly on Mondays.
- `src/graphql/schema.ts` — Add SensorSummaryReport type + dailySummary/weeklySummary queries
- `src/domains/report/queries.ts` — ReportQueries: findDailySummary(farmId, date), findWeeklySummary(farmId, weekStart)
- `src/domains/report/resolver.ts` — Resolver for summary queries

---

## Phase 3: RIC-160 Modules

### Module 2.5.2 — Farmer Profile
- `src/domains/farmer-profile/queries.ts` — FarmerProfileQueries: syncProfile(userId, surveyId) merges LINE profile + survey data into farmerProfiles, findByUserId, updateProfile
- `src/domains/farmer-profile/resolver.ts` — GraphQL: farmerProfile(userId), syncFarmerProfile(userId, surveyId) mutation, updateFarmerProfile mutation
- `src/graphql/schema.ts` — Add FarmerProfile type + queries/mutations

### Module 2.5.3 — Yield Data
- `src/domains/yield-ai/queries.ts` — Add recordActualYield(input) inserting into historicalYields, findYieldComparison(farmId, cropId) joining historicalYields + yieldPredictions
- `src/domains/yield-ai/resolver.ts` — Add recordActualYield mutation, yieldComparison query
- `src/graphql/schema.ts` — Add YieldComparison type + mutation + query

### Module 2.5.4 — Pest Report Generator
- `src/domains/pest-report/queries.ts` — PestReportQueries: generatePestReport(farmId) auto-generates from ricepestObservations + sensor anomalies (threshold breaches), findPestReports(farmId, status)
- `src/domains/pest-report/resolver.ts` — GraphQL: pestReports(farmId), generatePestReport(farmId) mutation
- `src/graphql/schema.ts` — Add PestReport type + query/mutation

### Module 2.5.5 — Cultivation Data
- `src/domains/crop/queries.ts` — Add updateCultivationData(cropId, input) for plantingMethod, variety, areaPlantedHectares updates
- `src/domains/crop/resolver.ts` — Add updateCultivationData mutation
- `src/graphql/schema.ts` — Add CultivationDataInput + mutation

### Module 2.5.6 — Field Condition Monitor
- `src/domains/sensor/reading-queries.ts` — Add findFieldConditions(farmId, periodDays?) method: aggregate sensor_readings by sensorType using time_bucket, compute avg/min/max, trend (compare current period vs previous)
- `src/domains/sensor/resolver.ts` — Add fieldConditions(farmId, period) query
- `src/graphql/schema.ts` — Add FieldCondition type (sensorType, avg, min, max, trend UP/DOWN/STABLE, sampleCount) + query

---

## Implementation Order

1. DB schema + migration (all tables at once)
2. RIC-159: Sync Manager (2.5.1)
3. RIC-159: Connection Monitor (2.5.8)
4. RIC-159: Batch Upload (2.5.9 refactor)
5. RIC-159: Device Auth (2.5.7)
6. RIC-159: Report Generator (2.5.10)
7. RIC-160: Farmer Profile (2.5.2)
8. RIC-160: Yield Data (2.5.3)
9. RIC-160: Pest Report (2.5.4)
10. RIC-160: Cultivation Data (2.5.5)
11. RIC-160: Field Condition (2.5.6)
12. GraphQL schema updates (batch all type additions)
13. Tests

## Key Patterns

- **Queries**: `class XxxQueries { constructor(private db: DB) {} }` returning `AppResult<T>`
- **Resolvers**: `ctx.requireAuth()` → `new XxxQueries(ctx.db)` → `result.map(toModel)` → throw on AppError
- **Cron**: `node-cron` with `start/stop/isRunning` exports
- **Consumer**: `startConsumer<T>(channel, queue, handler)` in mod.ts
- **Alert**: `publishAlert({ alertId, farmId, severity, title, message, category, metadata, createdAt })`
- **Migration**: Hand-written SQL in `drizzle/migrations/`
- **Schema**: All Drizzle tables in single `src/db/schema/index.ts`
