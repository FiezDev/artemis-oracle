---
name: iso-doc-creator
description: Generate ISO 9001-compliant documentation (Software Components #13, Software Design #15, Test Report #19) as bilingual EN + TH .docx files for any software project. Use this skill whenever the user asks to create ISO docs, generate compliance documentation, produce Software Components / Software Design / Test Report documents, or mentions ISO 9001 documentation — even if they just say "create the docs" or "generate ISO docs" or mention document numbers like #13, #15, #19. Drives capture via agent-browser, renders mermaid diagrams via mmdc, writes docx via python-docx.
---

# ISO Document Creator

Generate ISO 9001:2015 compliant documentation for software projects. One command produces six files — three doc types × two languages:

- **DOC-{CODE}-CMP-013** — Software Components Document (EN + `_TH`)
- **DOC-{CODE}-DES-015** — Software Design Document, Web (EN + `_TH`)
- **DOC-{CODE}-TST-019** — Test Report (EN + `_TH`)

## Workflow

The skill is **config-driven**. Write one JSON file, point the generator at it, done. Everything else — route discovery, login, language switching, screenshot capture, diagram rendering, docx assembly — is automatic.

### Step 1 — Author `iso-doc.json`

Lives in the **target repo root** (e.g., `/home/bjgdr/dev-work/<project>/iso-doc.json`) so each repo owns its own ISO config and a single command can regenerate docs across many projects. Example (DAD):

```json
{
  "project": {
    "name": "DAD Asset Management System",
    "code": "DAD",
    "description": "Thai real estate asset management platform..."
  },
  "urls": {
    "github":     "https://github.com/go-thailand/DAD-Asset-Management-System",
    "local_repo": "/home/bjgdr/dev-work/DAD-Asset-Management-System",
    "live":       "http://localhost:3000"
  },
  "auth": {
    "vault_key": "DAD-Asset-Management-System",
    "mode":      "form_password",
    "role":      "admin"
  },
  "routes": {
    "frontend_path":   "frontend/app",
    "include_dynamic": true,
    "ignore":          ["api", "_components", "_utils"]
  },
  "languages":  ["en", "th"],
  "docs":       ["13", "15", "19"],
  "output_dir": "/mnt/c/Users/bjgdr/OneDrive/Documents/ISODOC/FinalTake/DAD",
  "diagrams_source": "/home/bjgdr/oracle/artemis-oracle/iso-docs/dadassets/diagrams",
  "architecture": {
    "modules": [
      {
        "id": "assets",
        "title": {"en": "Asset Management", "th": "การจัดการทรัพย์สิน"},
        "description": {"en": "...", "th": "..."},
        "diagram": "dad-module-assets"
      }
    ],
    "integrations": [
      {
        "id": "flowaccount",
        "title": {"en": "FlowAccount Sync", "th": "การเชื่อมต่อ FlowAccount"},
        "description": {"en": "...", "th": "..."},
        "diagram": "dad-integration-flowaccount"
      }
    ]
  }
}
```

`architecture.modules[]` → doc15 section 4.x (per-module detail + diagram).
`architecture.integrations[]` → doc15 section 10.x (per-integration detail + diagram).
All diagrams named `<stem>.png` resolved from `assets/diagrams/`.

Fixed defaults (do not ask): Author `Ittipol Vongapai`, Organization `go-thailand`, Status `Approved`, Classification `Internal`, Version `1.0`.

Credentials go in `~/.claude/dev-vault/<vault_key>.json` — never in the config.

### Step 2 — Put the target app on `main` and start it

**Never capture from a feature branch.** Screenshots must reflect shipped, working features — not half-built WIP. Before every `--capture` run:

```bash
cd $LOCAL_REPO
git stash push -u -m "iso-capture-$(date +%s)"   # if there are local changes
git checkout main
# start the app — prefer the repo's own script over hand-rolling docker compose:
./start.sh   || ./run.sh   || docker compose -f docker-compose.local.yml up -d   || bun dev
```

Capture target can be prod (`urls.live: https://<prod>.com`) if the dev-vault creds are valid there — prod URLs are preferred when reachable because they reflect shipped state. Fall back to `http://localhost:<port>` if prod is unreachable from WSL.

Restore afterward: `git checkout <prev-branch> && git stash pop`.

### Step 3 — Run the generator

```bash
cd ~/oracle/artemis-oracle/.claude/skills/iso-doc-creator/scripts
python3 run.py \
  --config-file "/mnt/c/.../FinalTake/iso-doc.json" \
  --analysis-file ./analysis_dad.py \
  --fresh --capture --diagrams \
  --diagrams-src ~/oracle/artemis-oracle/iso-docs/<project>assets/diagrams
```

Flags:

| Flag | Purpose |
|------|---------|
| `--config-file` | Path to `iso-doc.json` (preferred). |
| `--analysis-file` | Optional Python module exporting `analysis = {...}` with curated tables, bilingual prose, and module metadata. Omit for auto-discovered routes + placeholder tables. |
| `--fresh` | Wipes `{output_dir}/*.docx` and `{output_dir}/assets/` before regen. |
| `--capture` | Launches `agent-browser` once per language: logs in via vault creds, switches UI language, walks every discovered route, skips error/alert pages, writes PNGs to `assets/screenshots/{lang}/{id}.png`. |
| `--diagrams` | Runs `mmdc` against `.mermaid` files whose source is newer than the `.png`. Copies all PNGs into `assets/diagrams/`. |

What happens internally:

1. `discover.walk()` — scans `frontend/app` for `page.tsx`/`page.ts`, emits `{id, route, is_dynamic, title_guess}`. `[locale]`/`[lang]`/`[language]` segments are substituted at capture time; other `[param]` segments mark the route dynamic (first-row-click capture).
2. `capture.capture_routes(cfg, routes, lang)` — once per language:
   - `wait_for_page_ready()` gates every shot (readyState complete + no active skeletons + primary content attached).
   - `dismiss_toasts()` clears transient Ant notifications.
   - `page_error_reason()` checks for Ant error surfaces, Next.js `nextjs-portal` shadow-DOM, and EN/TH runtime-error text markers. On match: retry once after 2 s, else skip + delete partial.
   - `font_missing_reason()` canvas-tests glyph widths; on tofu → `inject_webfont(lang)` injects Google Fonts Noto Sans Thai and **retakes the shot** (never rejects).
3. `diagrams.sync()` — mtime-based drift detection; only changed Mermaid sources re-render. Auto-runs when `iso-doc.json` has `diagrams_source`.
4. `doc13.build / doc15.build / doc19.build` loop over `config.LANGUAGES × config.DOCS`. `_TH` suffix appended via `config.output_path()`. Diagram allocation follows Rule 8 (13 = high-level only; 15 = architecture + modules + integrations; 19 = none).

### Step 4 — Verify output

Open each generated `.docx` and confirm:

- Cover page metadata present and correct.
- Section 3 (frontend components in doc13) only shows working features.
- **Same set of modules** in EN and TH section 3 (intersection rule, #1 below).
- Screenshots render, Thai glyphs aren't tofu boxes. No error overlays visible in any shot.
- Tables have bold headers, page breaks land correctly.
- **Images fit the page, caption stays with the image** (Rule 7). No image overflows, no orphaned captions.
- **Diagram allocation is correct** (Rule 8): doc13 has one high-level diagram; doc15 has architecture + per-module + per-integration; doc19 has zero diagrams.
- **TH doc body reads as Thai prose** — only proper nouns in English (Rule 9).
- No `[Image not found]` placeholder anywhere — if it appears, generation aborted and this is a bug (Rule 2).

Quick diagram check (hash-match embedded images against `assets/diagrams/`):

```bash
python3 -c "
import zipfile, hashlib, os
diags = {hashlib.md5(open(f'assets/diagrams/{f}','rb').read()).hexdigest(): f
         for f in os.listdir('assets/diagrams') if f.endswith('.png')}
for d in ['13_*', '15_*', '19_*']:
    # count how many diagram PNGs each docx embeds
    ..."
```

## Core Rules (must not violate)

### 1. Bilingual intersection — a route must work in ALL configured languages to appear

`config.common_screenshot_ids()` returns the set of screenshot IDs present in every `lang_screenshots_dir(lang)`. `doc13.py` section 3, `doc13.py` Appendix A, `doc15.py` Appendix A, and `doc19.py` Appendix A all filter by this set.

If a page errors in TH but works in EN (or vice versa), it is omitted from **both** language docs — the EN and TH deliverables must describe the exact same feature set. Skipped routes still appear in `doc13.py` Appendix C (complete route inventory) so total coverage is never hidden.

### 2. Image references fail loudly

`core.add_image()` raises `FileNotFoundError` if the image is missing. It never writes a `[Image not found: FE-001.png]` placeholder. That placeholder in a delivered doc is a defect, not a graceful fallback — the correct response is "the capture didn't produce the file, fix the capture or the lookup ID".

### 3. Main branch only for capture

Feature branches ship partially built or broken code. Screenshots from them are not deliverable. Stash, checkout `main`, run capture, restore branch. Applies every time `--capture` is used.

### 4. No error / alert states in screenshots

`capture.py:page_error_reason()` detects error surfaces and `dismiss_toasts()` runs before every shot so transient notifications never leak in. Detectors include:

- Ant Design selectors (`.ant-result-error`, `.ant-alert-error`, `.ant-notification-notice-error`, `.ant-message-error`)
- Next.js error overlays: `nextjs-portal` (with shadow-DOM traversal), `[data-nextjs-dialog]`, `[data-nextjs-toast-errors-parent]`, `.nextjs-container-errors-header`
- Plain-text markers in EN *and* TH: `Unhandled Runtime Error`, `Unidentified Runtime Error`, `Hydration failed`, `ReferenceError:`, `TypeError:`, `Failed to load`, `เกิดข้อผิดพลาด`, `ไม่พบหน้า`

On match: retry once after 2 s, else skip (delete any partial file). Never disable the detector without explicit user permission.

### 5. Page must fully load before every shot

`capture.py:wait_for_page_ready(timeout=12.0, settle=1.5)` gates every screenshot. It polls `document.readyState === 'complete'`, rejects visible `.ant-skeleton-active` / `.ant-spin-spinning`, and waits for primary content to attach. Only after this gate passes does `take_screenshot()` fire.

### 6. Tofu glyphs → inject font + retake, never reject

If the TH screenshot shows missing-glyph boxes (`□ □ □`), `capture.py:font_missing_reason(lang)` detects it via canvas `measureText()` comparison vs U+E000. On detection: `inject_webfont(lang)` injects Google Fonts Noto Sans Thai via `<link>` + `<style>`, awaits `document.fonts.ready`, and the shot is retaken. **Never skip or reject on tofu** — font fallback is the only correct response.

### 7. Image must fit the page, caption must stay with image

`core.add_image()` caps picture size at 6.0" wide × 7.0" tall (aspect-preserved via PNG IHDR parse). The image paragraph carries `keep_with_next = True` and the caption paragraph carries `keep_together = True`, so Word always binds caption to its image on the same page — image+caption are pushed to the next page together if they don't fit.

### 8. Diagram allocation per doc type (no duplicates across docs)

Strict ownership — each diagram belongs to exactly one document:

| Doc | Allowed diagrams | Rationale |
|-----|------------------|-----------|
| **13 Components** | `system-overview` only | High-level "what it is", one figure |
| **15 Design** | Architecture set (deployment, access-control, data-flow, ERD) + **per-module** + **per-integration** | Detail for each function / integration |
| **19 Test Report** | **Zero diagrams** | Tests only — tables for pipeline, coverage gaps, results |

Config drives it: `architecture.modules[].diagram` and `architecture.integrations[].diagram` point at PNG stems in `assets/diagrams/`. Appendix "diagram dump" sections are forbidden — they duplicate content across every doc.

### 9. TH doc is Thai prose — not English with Thai cover page

Fixed strings come from `strings.py:STRINGS[lang][key]` (Thai values, EN fallback). Project prose (description, module bios, features) reads bilingual dicts: `{"en": "...", "th": "..."}`. When writing TH content, use Thai prose throughout — English appears **only** for proper nouns and industry-standard tech terms (API, JWT, RBAC, CRUD, HTTP, S3, FlowAccount, Tesseract, Python, etc.). A TH doc whose body is mostly English is a defect.

### 10. Skill code holds zero project data

The skill is 100% generic. Every project-specific value — name, code, URLs, modules, integrations, tech stack, diagram list, analysis prose — lives in `iso-doc.json` (in the target repo root) and optional `analysis_<project>.py`. The skill's `scripts/` directory must contain no project-named constants, no hardcoded module lists, no repo-specific tables. If you find yourself wanting to edit the skill code to accommodate a new project, the change belongs in the project's config instead.

## Repository layout

```
.claude/skills/iso-doc-creator/
├── SKILL.md                  (this file)
├── references/
│   └── iso-templates.md      section-by-section doc templates
└── scripts/
    ├── run.py                CLI entry, orchestrates capture → diagrams → doc loop
    ├── config.py             ProjectConfig.from_json(), common_screenshot_ids()
    ├── discover.py           walk(repo, frontend_path) → routes
    ├── capture.py            agent-browser driver (login, language switch, capture, error skip)
    ├── diagrams.py           sync(src, dst) mtime drift renderer, shells out to mmdc
    ├── strings.py            STRINGS dict + T(lang, key, **fmt) — ~60 bilingual keys
    ├── core.py               add_cover_page, add_revision_history, add_toc,
    │                         add_table, add_image (fail-fast), add_bullet_list
    ├── doc13.py              Software Components (#13) — data-driven section 3
    ├── doc15.py              Software Design (#15)
    ├── doc19.py              Test Report (#19)
    └── analysis_<project>.py optional curated overrides (bilingual prose, tables)
```

## Analysis file (optional)

`analysis_<project>.py` exports `analysis = {...}` to override auto-discovery with curated content:

```python
analysis = {
    "description": {"en": "...", "th": "..."},     # or just a string
    "tech_stack":        [(layer, component, tech, version), ...],
    "api_services":      [(id, service, base_path, description), ...],
    "db_tables":         [(table, description, key_fields), ...],
    "infrastructure":    [(component, tech, purpose, deployment), ...],
    "external_services": [(service, provider, purpose, integration), ...],
    "security":          [(component, mechanism, description), ...],
    # frontend_modules intentionally omitted — discover.walk() fills these in.
    # Override only if you need curated bilingual titles/descriptions.
}
```

Any key can be omitted — the generator falls back to defaults or discovery.

**Do not maintain a hardcoded `frontend_modules` list that doesn't match capture output.** Stale ID mismatches (`FE-001.png` in the list, `FE-dashboard.png` in capture) were the root cause of every `[Image not found]` incident. Let `discover.walk()` own the ID space.

## Dependencies

```bash
pip install python-docx
npm install -g @mermaid-js/mermaid-cli          # provides mmdc
brew install vercel-labs/tap/agent-browser      # provides agent-browser
/home/bjgdr/.linuxbrew/bin/agent-browser install  # installs headless Chrome (first time)
```

For TH screenshots to render glyphs (not tofu boxes), the headless Chrome needs Thai fonts — `fonts-thai-tlwg` on Debian/Ubuntu. If `assets/screenshots/th/` is empty after capture, the generators fall back to the EN set and you lose the language differentiation.

## Bibliography

- `references/iso-templates.md` — section-by-section templates for #13, #15, #19
- `/home/bjgdr/oracle/artemis-oracle/iso-doc-creation-guide.md` — ISO theory, numbering conventions, quick reference
