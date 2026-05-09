"""Route auto-discovery for Next.js app-router projects.

Walks <repo>/<frontend_path> for page.tsx/page.ts files, emits a list of
route descriptors. Dynamic segments like [id] are flagged so the capture
step knows to navigate via list -> first-row click.
"""

import os
import re

PAGE_FILES = ("page.tsx", "page.ts", "page.jsx", "page.js")
SKIP_DIRS = {"node_modules", ".next", ".next-tmp", "__tests__", "__mocks__"}
# i18n placeholder segments — not truly dynamic; substituted with the current lang
I18N_SEGMENTS = {"locale", "lang", "language"}


def walk(repo_root, frontend_path="frontend/app", ignore=None):
    """Return list of dicts: {id, route, is_dynamic, dynamic_segments, dir}.

    ignore: list of top-level app subfolders to skip (e.g. ["api", "_components"]).
    """
    ignore = set(ignore or [])
    app_dir = os.path.join(repo_root, frontend_path)
    if not os.path.isdir(app_dir):
        return []

    routes = []
    seen_counts = {}

    for dirpath, dirnames, filenames in os.walk(app_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]

        rel = os.path.relpath(dirpath, app_dir)
        if rel == ".":
            rel_parts = []
        else:
            rel_parts = rel.split(os.sep)

        top = rel_parts[0] if rel_parts else ""
        if top in ignore:
            continue

        if not any(p in filenames for p in PAGE_FILES):
            continue

        route_parts = []
        dynamic_segments = []
        skip = False
        for part in rel_parts:
            if part.startswith("(") and part.endswith(")"):
                continue
            if part.startswith("@"):
                skip = True
                break
            if part.startswith("[") and part.endswith("]"):
                seg = part.strip("[]").lstrip(".")
                if seg not in I18N_SEGMENTS:
                    dynamic_segments.append(seg)
            route_parts.append(part)
        if skip:
            continue

        route = "/" + "/".join(route_parts) if route_parts else "/"
        is_dynamic = len(dynamic_segments) > 0

        module_id = _derive_id(route_parts, seen_counts, is_dynamic)
        routes.append({
            "id": module_id,
            "route": route,
            "is_dynamic": is_dynamic,
            "dynamic_segments": dynamic_segments,
            "dir": dirpath,
            "title_guess": _title_guess(route_parts),
        })

    routes.sort(key=lambda r: r["route"])
    return routes


def _derive_id(parts, seen_counts, is_dynamic):
    base_parts = [p for p in parts
                  if not (p.startswith("[") and p.endswith("]"))]
    base = "home" if not base_parts else "-".join(base_parts)
    suffix = "-detail" if is_dynamic else ""
    key = f"FE-{base}{suffix}"
    n = seen_counts.get(key, 0) + 1
    seen_counts[key] = n
    return key if n == 1 else f"{key}-{n}"


def _title_guess(parts):
    if not parts:
        return "Home"
    clean = [p for p in parts
             if not (p.startswith("[") and p.endswith("]"))]
    if not clean:
        return "Detail"
    return " ".join(w.capitalize() for w in re.split(r"[-_]", clean[-1]))


def build_url(base_url, route, lang="en", sample_ids=None):
    """Substitute [locale] with lang and any [param] with sample_ids[param] or ''."""
    sample_ids = sample_ids or {}
    parts = []
    for seg in route.strip("/").split("/"):
        if seg.startswith("[") and seg.endswith("]"):
            name = seg.strip("[]").lstrip(".")
            if name in I18N_SEGMENTS:
                parts.append(lang)
            else:
                parts.append(sample_ids.get(name, ""))
        else:
            parts.append(seg)
    path = "/".join(p for p in parts if p)
    return f"{base_url.rstrip('/')}/{path}" if path else base_url.rstrip("/")


def walk_vue(repo_root, router_file="src/router/index.js", prefix=""):
    """Extract routes from a Vue Router config file via brace-depth parsing.

    Handles both flat arrays and `children: [...]` nesting. Routes with
    `redirect:` (no component) are skipped — they're navigation shims, not
    real pages.

    Returns list of {id, route, is_dynamic, title_guess}. IDs are prefixed
    with `FE-{prefix}-` if prefix given, else `FE-`.
    """
    full = os.path.join(repo_root, router_file)
    if not os.path.isfile(full):
        return []
    with open(full) as f:
        text = f.read()

    text = _strip_js_comments(text)

    routes = []
    # Per depth: the first `path:` value we see, the name, and whether this
    # object had a `component:` key (skip objects with only `redirect:`).
    path_at = {}
    name_at = {}
    has_component_at = {}
    redirect_at = {}
    depth = 0
    i = 0
    n = len(text)
    path_re = re.compile(r'path\s*:\s*["\']([^"\']*)["\']')
    name_re = re.compile(r'name\s*:\s*["\']([^"\']*)["\']')
    comp_re = re.compile(r'component\s*:')
    redirect_re = re.compile(r'redirect\s*:\s*["\']([^"\']*)["\']')

    seen_counts = {}
    while i < n:
        c = text[i]
        if c == '"' or c == "'" or c == '`':
            # Skip string literal
            quote = c
            i += 1
            while i < n and text[i] != quote:
                if text[i] == '\\':
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if c == '{':
            depth += 1
            path_at[depth] = None
            name_at[depth] = None
            has_component_at[depth] = False
            redirect_at[depth] = None
            i += 1
            continue
        if c == '}':
            # Close an object — if it describes a page, emit a route.
            if path_at.get(depth) is not None and has_component_at.get(depth) \
                    and redirect_at.get(depth) is None:
                parts = [path_at[d] for d in sorted(path_at) if d < depth and path_at.get(d)]
                parts.append(path_at[depth])
                route = _join_vue_paths(parts)
                is_dynamic = ":" in route
                pid = _derive_vue_id(route, name_at.get(depth), seen_counts, prefix)
                routes.append({
                    "id": pid,
                    "route": route,
                    "is_dynamic": is_dynamic,
                    "title_guess": _vue_title(route, name_at.get(depth)),
                })
            path_at.pop(depth, None)
            name_at.pop(depth, None)
            has_component_at.pop(depth, None)
            redirect_at.pop(depth, None)
            depth -= 1
            i += 1
            continue

        m = path_re.match(text, i)
        if m and path_at.get(depth) is None and depth > 0:
            path_at[depth] = m.group(1)
            i = m.end()
            continue
        m = name_re.match(text, i)
        if m and name_at.get(depth) is None and depth > 0:
            name_at[depth] = m.group(1)
            i = m.end()
            continue
        m = comp_re.match(text, i)
        if m and depth > 0:
            has_component_at[depth] = True
            i = m.end()
            continue
        m = redirect_re.match(text, i)
        if m and depth > 0:
            redirect_at[depth] = m.group(1)
            i = m.end()
            continue
        i += 1

    # Dedupe by route (same path can appear via aliases)
    seen_routes = set()
    unique = []
    for r in routes:
        if r["route"] in seen_routes:
            continue
        seen_routes.add(r["route"])
        unique.append(r)
    unique.sort(key=lambda r: r["route"])
    return unique


def _strip_js_comments(text):
    """Strip // line comments and /* */ block comments. Leaves strings intact
    (approximately — fine for router config files)."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i+1] == '/':
            i += 2
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and text[i+1] == '*':
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i+1] == '/'):
                i += 1
            i += 2
            continue
        if c in ('"', "'", '`'):
            out.append(c)
            i += 1
            while i < n and text[i] != c:
                if text[i] == '\\' and i + 1 < n:
                    out.append(text[i]); out.append(text[i+1]); i += 2
                else:
                    out.append(text[i]); i += 1
            if i < n:
                out.append(text[i]); i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _join_vue_paths(parts):
    """Join Vue Router path segments. Absolute segments reset the chain."""
    result = ""
    for p in parts:
        if not p:
            continue
        if p.startswith("/"):
            result = p
        else:
            if result and not result.endswith("/"):
                result += "/"
            result += p
    # Normalize trailing slash unless root
    if len(result) > 1 and result.endswith("/"):
        result = result[:-1]
    return result or "/"


def _derive_vue_id(route, name, seen_counts, prefix):
    base = (name or route.strip("/").replace("/", "-").replace(":", "") or "home")
    base = re.sub(r"[^a-zA-Z0-9_-]", "-", base).strip("-").lower()
    base = base or "home"
    pid_prefix = f"FE-{prefix}-" if prefix else "FE-"
    key = f"{pid_prefix}{base}"
    n = seen_counts.get(key, 0) + 1
    seen_counts[key] = n
    return key if n == 1 else f"{key}-{n}"


def _vue_title(route, name):
    if name:
        return " ".join(w.capitalize() for w in re.split(r"[-_]", name))
    tail = route.strip("/").split("/")[-1] if route != "/" else "home"
    tail = re.sub(r":[^/]+", "", tail).strip("-") or "home"
    return " ".join(w.capitalize() for w in re.split(r"[-_]", tail))


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 discover.py <repo_root> [frontend_path_or_vue_router] [--vue] [--prefix=X]")
        sys.exit(1)
    repo = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else "frontend/app"
    is_vue = "--vue" in sys.argv
    prefix = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--prefix=")), "")
    if is_vue:
        print(json.dumps(walk_vue(repo, path, prefix=prefix), indent=2))
    else:
        print(json.dumps(walk(repo, path), indent=2))
