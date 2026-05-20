# RIC-301 — Restore LINE + Firebase + SMS credentials in prod

## Role

You are a senior SRE-leaning backend engineer with prod ops authority on the RiceGuard alert system. You have **AWS SSM Session Manager** access to the production API EC2 (no plain SSH from CI — see CI/CD note below), console access to the LINE Developers Console (channel 2009081199) and Firebase project (RiceGuard prod). You are working alone but communicate state changes clearly in writing. You understand that this ticket is a credential-recovery operation, not a code change.

## Objective

Restore the LINE channel access token, Firebase service-account credentials, and SMS gateway credentials in the `riceguard-api` production container so that all three outbound alert channels (LINE, FCM, SMS) resume delivery. All three are silently failing since the prod cutover on 2026-05-06.

## Context

<existing_context>
**Repo:** `/home/bjgdr/dev-work/RG/Rice-Guard-API` (branch `develop`)
**Stack:** Bun + Elysia + GraphQL Yoga + Drizzle ORM + TimescaleDB + RabbitMQ + Redis + Firebase Admin + LINE Messaging API
**Prod host:** EC2 instance (`t4g.medium` arm64) running `docker compose` from `/opt/riceguard/`
**Env file:** `/opt/riceguard/env/.env` (managed on host — NOT pushed from CI per `.github/workflows/README-CICD.md`)
**Deploy model:** SSM-based (prod) / SSH-based (staging). The prod EC2's `.env` files are managed on the host, which is **why the 2026-05-06 cutover dropped these vars** — CI never had them to redeploy.
**Audit source:** 2026-05-20 alert system audit (Boris #102 follow-up)

**Prod access path (verified 2026-05-20 against handover docs + `.github/workflows/README-CICD.md`):**
- The actual prod EC2 (the one running `api.riceguard.ai` behind ALB target group `tg-api-prod-prod`) has **no public IP and no SSH ingress** per `riceguard-prod-handover/06-runbook.md:5`. SSM Session Manager is the only way in.
- Use `aws ssm start-session --target <instance-id>` to reach the prod host. The instance carries `IAMRole-riceguard-prod` (`AmazonSSMManagedInstanceCore` managed + inline S3 backups policy).
- If the `riceguard-prod-cicd` IAM user is not yet provisioned (the CI README flags this as outstanding), the agent operating this ticket must have its own IAM credentials with `ssm:StartSession` on the riceguard-tagged EC2s.
- Once on the host, `cd /opt/riceguard && sudo docker compose up -d --force-recreate riceguard-api`.

**Definitive credential-hunt findings (verified 2026-05-20 against the actual prod EC2 `i-0aa46f0468a9fd61e` via SSM Session Manager — instance name `Rice Guard Prod API`, region `ap-southeast-7`):**

**Narrative correction:** The audit's framing ("creds were dropped in cutover") is partially wrong. Reality:

- The prod `.env` was generated `2026-05-05T10:43:40+07:00` (one day **before** the cutover).
- Its leading comments explicitly say `# LINE messaging — copied from staging` and `# AWS (kept from staging — same SQS region until prod has its own)`.
- Staging has never had real LINE/Firebase/SMS credentials.
- Therefore prod inherited **placeholders**, not real values that later "got dropped."

**Specifically, on prod's `/opt/riceguard/env/.env` (size 2910 bytes, mode 600, last touched 2026-05-12):**

| Variable | Value characteristic | Verdict |
|---|---|---|
| `LINE_CHANNEL_ID` | 10 chars, prefix `200...` | Matches documented channel `2009081199` — likely real |
| `LINE_CHANNEL_SECRET` | 32 chars, prefix `CHA...` | Almost certainly placeholder (`CHA` prefix shared with the token below) |
| `LINE_CHANNEL_ACCESS_TOKEN` | 31 chars, prefix `CHA...` | **Confirmed placeholder.** Live-tested against `https://api.line.me/v2/bot/info` → `HTTP 401 "Authentication failed."` Real LINE long-lived tokens are ~170+ chars; 31 chars = `CHANGE_ME_..._PLACEHOLDER` shape. |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY` | **Absent from `.env` entirely** | Never configured on this prod environment |
| `SMS_USER`, `SMS_PASS`, `SMS_URL`, `SMS_SENDER` | **Absent from `.env` entirely** | Never configured |
| `FCM_*`, `GOOGLE_*`, `ALERT_PHONE_NUMBER` | **Absent from `.env` entirely** | Never configured |

**Cross-checked sources that have NO real values either:**

| Source | Result |
|---|---|
| Staging EC2 `rice-guard-staging` container env | `LINE_*` are empty strings; no Firebase or SMS vars |
| Staging EC2 `/home/ec2-user/rice-guard-api/.env` | `your-...-here` placeholders for LINE; nothing else |
| GitHub Secrets `PROD_*` prefix | Does not exist |
| GitHub Secrets unprefixed (legacy `LINE_CHANNEL_ACCESS_TOKEN` etc.) | All deleted in cutover commit `4e61606` |
| GitHub Secrets `STAGING_LINE_*` | 3 secrets exist (created 2026-05-06 09:10 UTC); no current workflow references them; values unverifiable without a temp `workflow_dispatch` |
| Handover zip `riceguard-prod-handover-v1.1.zip` | Documentation only; explicitly states "no central secret manager" |
| `.env.bak.1778210615` (prod, dated 2026-05-08) | Same placeholder values — no regression to roll back to |

**This means RIC-301 is a fresh-issuance task, not a restoration task.**

**Practical sequence for the executor:**

1. **Step 0 — verify LINE_CHANNEL_ID + LINE_CHANNEL_SECRET against the LINE Developers Console** for channel `2009081199`. The `200...`-prefixed channel ID is almost certainly real (matches Boris #102 docs); the secret may also be real. If both are real, only the access token needs rotation. If the secret is also placeholder, rotate the channel secret too.
2. **Step 1 — issue a fresh LINE long-lived access token (v2.1)** via the LINE Developers Console → channel `2009081199`. Token should be 170+ chars. Write to `/opt/riceguard/env/.env` on the prod EC2 (`i-0aa46f0468a9fd61e`) over SSM, then `docker compose up -d --force-recreate riceguard-api`.
3. **Step 2 — add Firebase service-account credentials** to prod's `.env`. Firebase Console → Project Settings → Service Accounts → Generate new private key (JSON). Extract `project_id`, `client_email`, `private_key`. Pay attention to the `\n` escaping requirement noted in `src/infrastructure/firebase/client.ts`.
4. **Step 3 — add SMS gateway credentials.** Locate the original Thai SOAP gateway vendor (per Boris #102 / `nt-tag-id-backend src/controllers/send_sms.controller.js`). **This is the highest-friction step — start the vendor contact first**, in parallel with Steps 1–2, so the SMS path isn't blocking everything else.
5. **Step 4 — once all values land:** restart, verify with the three probes in "Success Criteria" below, then 30-min observation.

**Useful artifacts captured during the cred hunt (in your local `/home/bjgdr/secret/` per privacy convention):**
- The prod EC2 instance ID: `i-0aa46f0468a9fd61e` (private IP `10.40.10.212`, behind ALB target group `tg-api-prod-prod`)
- AWS account: `654654475577`, region: `ap-southeast-7`
- IAM user that has SSM access from a local shell: `ittipol-aws` (the same one being used by the executor of this ticket)

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
