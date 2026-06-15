# Ittipol Vongapai — CV / Resume

Rebuilt **15 June 2026**. ATS-clean, performance/impact-based, AI subtle-but-proven.
Minimal layout, **Arial** (matches the old CV), **blue name accent** (`#1D4ED8`).

## Source files (edit `build_cv.py`, not these — they're generated)

| File | What |
|---|---|
| `resume.md` / `resume.txt` | **International — full** (2 pages). Primary. |
| `resume-onepage.md` / `.txt` | **International — 1 page.** |
| `resume-th.md` / `.txt` | **Thai-market variant** — DOB + nationality in header, photo slot in PDF. |
| `resume.legacy-2026-05.*` | Backup of the original May-2026 draft (nothing deleted). |

## Deliverables (`dist/`)

| File | Use |
|---|---|
| `Ittipol_Vongapai_CV.pdf` | International full, 2 pp. Recruiter-facing. |
| `Ittipol_Vongapai_CV_1page.pdf` | International, 1 page. |
| `Ittipol_Vongapai_CV_TH.pdf` | Thai-market, 2 pp (photo box top-right). |
| `Ittipol_Vongapai_CV.docx` / `_1page.docx` | ATS upload (.docx preferred by many ATS). |
| `ittipol_cv_v2.pdf` | **Drop-in replacement** for the live site (same filename). |

## What changed this round

- **GitHub Activity removed** — the whole section + every contribution/commit number scrubbed
  from summary, experience and education.
- **Selected Projects = portfolio AI work only** — AtEase, ORG-TOOLS, Vehicle Verifier,
  Image Crawler & Labelling. (QOne / Oracle / git-doc dropped — not on the portfolio;
  Portfolio & FlightClone dropped per request.)
- **Cleaner & minimal** — more whitespace, blue section rules, decluttered experience bullets.
- **Arial** font (matches old CV); blue name accent (`#1D4ED8`).

## Update the live site

Upload `dist/ittipol_cv_v2.pdf` to Firebase Storage path `cv/ittipol_cv_v2.pdf`
(portfolio Download-CV button → `ImgixImage.cv_pdf2`). Purge imgix cache after.

## ATS hardening

Single column · standard headings · selectable text (verified) · ligatures disabled
(`fiez.dev`/`proficiency` extract char-by-char) · flexbox dates keep reading order · Arial ·
no layout tables · 24/24 target keywords present.

## Regenerate

```bash
python3 -m venv /tmp/cvenv && /tmp/cvenv/bin/pip install pypdf python-docx
/tmp/cvenv/bin/python build_cv.py     # builds in /tmp, deploys here with friendly names
```
Requires Google Chrome (HTML→PDF). Override target dir with `CV_DEST=...`.

## Notes / judgment calls

- **Experience** is real employment (Go Thailand → 7Solutions → NestiFly → Fusion). Go Thailand is
  led by RiceGuard + vehicle/person-recognition work (both on the portfolio); a brief line covers the
  multi-tenant CCTV SaaS + tax SaaS (real work, though not shown on the portfolio — say the word to trim).
- **AI** is woven through real systems built (LLM pipelines, agents, MCP, CV models) — no buzzword padding.
- **Education** framed as "Education & Continuous Learning" (secondary education + self-taught); no gap spotlight.
