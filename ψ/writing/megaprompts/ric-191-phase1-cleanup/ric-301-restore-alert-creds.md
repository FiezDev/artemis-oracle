# RIC-301 — Restore LINE + Firebase + SMS credentials in prod

## Role

You are a senior SRE-leaning backend engineer with prod ops authority on the RiceGuard alert system. You have SSH to the production API EC2, console access to the LINE Developers Console (channel 2009081199) and Firebase project (RiceGuard prod). You are working alone but communicate state changes clearly in writing. You understand that this ticket is a credential-recovery operation, not a code change.

## Objective

Restore the LINE channel access token, Firebase service-account credentials, and SMS gateway credentials in the `riceguard-api` production container so that all three outbound alert channels (LINE, FCM, SMS) resume delivery. All three are silently failing since the prod cutover on 2026-05-06.

## Context

<existing_context>
**Repo:** `/home/bjgdr/dev-work/RG/Rice-Guard-API` (branch `develop`)
**Stack:** Bun + Elysia + GraphQL Yoga + Drizzle ORM + TimescaleDB + RabbitMQ + Redis + Firebase Admin + LINE Messaging API
**Prod host:** EC2 instance running `docker compose` from `/opt/riceguard/`
**Env file:** `/opt/riceguard/env/.env`
**Audit source:** 2026-05-20 alert system audit (Boris #102 follow-up)

**Audit findings:**

1. **LINE token INVALID (401).** Inside the `riceguard-api` container:
   ```
   curl -H "Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN" https://api.line.me/v2/bot/info
   {"message":"Authentication failed. Confirm that the access token in the authorization header is valid."}
   HTTP 401
   ```
   Token present in env but rejected. Channel ID: `2009081199` (RiceGuard alert OA). 0 LINE rows in `alert_delivery_log` over 7 days.

2. **Firebase credentials MISSING.** `env | grep -E '^FIREBASE_|^FCM_|^GOOGLE_'` returns empty. Container logs show `[Firebase] No credentials found. Push notifications disabled.` Required env per `src/infrastructure/firebase/client.ts`:
   - `FIREBASE_PROJECT_ID`
   - `FIREBASE_CLIENT_EMAIL`
   - `FIREBASE_PRIVATE_KEY` (with literal `\n` for newlines)

   Result: 773 FCM rows `skipped_gateway_down` in last 7 days.

3. **SMS gateway MISSING.** No `SMS_USER`, `SMS_PASS`, `SMS_URL`, `SMS_SENDER` present. Container logs: `[SMS Consumer] SMS gateway not configured, skipping`. Required env per `src/infrastructure/sms/index.ts`:
   - `SMS_USER`
   - `SMS_PASS`
   - `SMS_URL`
   - `SMS_SENDER`
   - `ALERT_PHONE_NUMBER` (optional fallback)

   Result: 309 SMS rows `skipped_gateway_down` in last 7 days (CRITICAL alerts only per Boris #102 SMS=CRITICAL-only policy).

**Suspected origin:** prod cutover 2026-05-06 (ALB/NLB DNS migration + container env reseed) — env vars were dropped during the migration.

**Sibling tickets (do NOT execute here, but be aware):**
- RIC-302 — LINE consumer silent-skip code fix (unblocks observability)
- RIC-303 — seed `users.line_user_id` (depends on this ticket for E2E)
- RIC-304 — FCM consumer silent-skip code fix
- RIC-305 — DLX consumer + cooldown / delivery_state / audit writers

**Jira:** https://mobileai.atlassian.net/browse/RIC-301
</existing_context>

## Examples

Reference files in the repo (read these — don't reimplement them):

- `src/infrastructure/firebase/client.ts` — Firebase env var contract
- `src/infrastructure/sms/index.ts` — SMS env var contract and `[SMS] Gateway configured` log line
- `src/consumers/line.consumer.ts` — how the LINE token is consumed (see `isLinePushAvailable()` and `getLinePushClient()`)

## Output Format

This ticket produces **no code changes** in the repo. Deliverables:

1. **Runbook file** committed to repo at `docs/runbooks/RIC-301-credential-restoration.md` on branch `ric-301-restore-alert-creds`:
   - Each step performed (LINE rotation, Firebase restoration, SMS restoration)
   - Verification commands and their outputs (redact secret values; keep curl HTTP status and log-line presence)
   - Timestamps for each restoration
   - 30-min observation window summary
2. **PR against `develop`** titled `docs(runbooks): RIC-301 — alert credential restoration runbook`
3. **Status update comment on Jira RIC-301** with the runbook PR link and the acceptance-criteria pass/fail table

Branch name: `ric-301-restore-alert-creds`
Commit format: `docs(runbooks): RIC-301 — <subject>` (conventional commits)

## Reasoning Approach

Sequential, fail-fast, one channel at a time. Verify each before moving to the next. If LINE token rotation fails, stop and report — don't proceed to Firebase. The order is: LINE → Firebase → SMS (the smallest blast radius first; SMS is CRITICAL-only and lowest volume).

For each channel:
1. Probe current broken state and record the symptom
2. Apply the fix (rotate / restore env vars)
3. `docker compose up -d --force-recreate riceguard-api`
4. Probe again, record success
5. Move on

After all three: 30-minute observation window watching `docker logs -f riceguard-api` for regressions (auth-fail loops, new errors, log spam).

## Constraints

**Hard NOs:**
- Never `git push --force` on any branch.
- Never run `git commit --no-verify` or otherwise skip pre-commit hooks. If a hook fails, fix the root cause.
- Never merge the PR autonomously — open it and request human review.
- Never write actual secret values to the runbook, Jira, or any committed file. Only record "rotated at HH:MM" and verification HTTP status / log-line presence.
- Never touch files outside `docs/runbooks/`. This ticket adds documentation only.
- Never proceed to the next channel if the prior channel's verification fails — stop and report.
- Never run `docker compose down` (destructive); only `up -d --force-recreate <service>`.
- If you cannot locate vendor SMS credentials, stop and request them — do not invent placeholder values.

**Required behaviors:**
- Before any container restart, `docker exec riceguard-api env | wc -l` to record baseline env count, and `docker exec riceguard-api date` to anchor the restart timestamp.
- After every restart, `docker logs --since 2m riceguard-api | grep -E '(Firebase|LINE|SMS)'` to confirm startup messages.
- 30-min observation window MUST be tailed and summarized — don't skip.

## Success Criteria

All must pass and be recorded in the runbook:

1. `docker exec riceguard-api curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN" https://api.line.me/v2/bot/info` returns `200`.
2. `docker logs riceguard-api 2>&1 | tail -200 | grep "\[Firebase\] No credentials found"` returns **empty** after restart.
3. `docker logs riceguard-api 2>&1 | tail -200 | grep "\[SMS Consumer\] SMS gateway not configured"` returns **empty** after restart.
4. After 30-min observation window, no recurring auth-fail loops or new error patterns in `docker logs riceguard-api`.
5. After siblings RIC-302 (silent-skip fix) and RIC-303 (line_user_id seed) ship, a test farm with seeded `line_user_id` receives a Flex card on next cron fire — note this is a **post-condition verified by RIC-303**, not by this ticket. This ticket's responsibility ends at "channels are configured and responsive."
6. PR opened, awaiting human merge. Jira comment posted with runbook link.

## Memory anchors

- **Land structural; defer verification when infra blocks.** If LINE token is rotated and verifies, but RIC-302 silent-skip fix hasn't landed yet, `alert_delivery_log` will still show 0 LINE rows. That's expected — don't chase it. Document the condition and move on.
- **Backport fixes to source.** If during execution you discover that the LINE/Firebase/SMS env var contract drifted between code and the runbook you're writing, update the runbook to match the code (not the other way around) and note the discrepancy in the PR description.
