#!/usr/bin/env python3
"""ISO Document Generator — generate docs in every configured language.

Two ways to invoke:

    # 1. All config via JSON (preferred — one file travels with the output)
    python3 run.py --config-file /path/to/iso-doc.json [--fresh] [--capture] [--diagrams]

    # 2. All config via CLI flags (legacy; still works)
    python3 run.py --project-name NAME --project-code CODE ... [--fresh]

Flags:
    --config-file     Path to iso-doc.json (overrides most other flags)
    --analysis-file   Optional Python file defining `analysis = {...}`
    --fresh           Wipe output dir .docx files and assets/ before regen
    --capture         Run capture.py for fresh screenshots (one pass per language)
    --diagrams        Sync mermaid -> png before generating docs
    --diagrams-src    Source dir for .mermaid files (when --diagrams is set)
"""

import argparse
import importlib.util
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ProjectConfig
import doc13
import doc15
import doc19


def parse_args():
    p = argparse.ArgumentParser(description="Generate ISO 9001 documentation")
    p.add_argument("--config-file", default="", help="Path to iso-doc.json")
    p.add_argument("--project-name", default="", help="Full project name")
    p.add_argument("--project-code", default="", help="3-letter code")
    p.add_argument("--description", default="")
    p.add_argument("--github-url", default="")
    p.add_argument("--local-repo", default="")
    p.add_argument("--system-url", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--assets-dir", default="")
    p.add_argument("--docs", default="", help="Comma-separated: 13,15,19")
    p.add_argument("--languages", default="", help="Comma-separated: en,th")
    p.add_argument("--analysis-file", default="")
    p.add_argument("--fresh", action="store_true",
                   help="Wipe output .docx and assets/ before regen")
    p.add_argument("--capture", action="store_true",
                   help="Run capture.py for fresh screenshots")
    p.add_argument("--diagrams", action="store_true",
                   help="Sync mermaid -> PNG before generation")
    p.add_argument("--diagrams-src", default="",
                   help="Source dir for .mermaid files")
    p.add_argument("--skip-login", action="store_true",
                   help="Skip automated login — assumes agent-browser session is already authenticated")
    return p.parse_args()


def load_analysis(filepath):
    """Return (static_dict, get_fn) where get_fn(lang) returns a per-lang dict.

    Supports two forms in the module:
      * analysis = {...}           — shared across languages
      * get_analysis(lang) -> {...} — per-language override (preferred when
                                       the Thai version needs fully-Thai prose)
    """
    if not filepath or not os.path.exists(filepath):
        return {}, None
    spec = importlib.util.spec_from_file_location("analysis", filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "analysis", {}), getattr(mod, "get_analysis", None)


def build_config(args):
    overrides = {
        "project_name": args.project_name,
        "project_code": args.project_code,
        "description": args.description,
        "github_url": args.github_url,
        "local_repo": args.local_repo,
        "system_url": args.system_url,
        "output_dir": args.output_dir,
        "assets_dir": args.assets_dir,
    }
    if args.docs:
        overrides["docs"] = args.docs.split(",")
    if args.languages:
        overrides["languages"] = args.languages.split(",")

    if args.config_file:
        if not os.path.exists(args.config_file):
            sys.exit(f"Config file not found: {args.config_file}")
        return ProjectConfig.from_json(args.config_file, **overrides)

    if not args.project_name or not args.project_code:
        sys.exit("Either --config-file or both --project-name and --project-code required")

    return ProjectConfig(
        project_name=args.project_name,
        project_code=args.project_code,
        description=args.description,
        github_url=args.github_url,
        local_repo=args.local_repo,
        system_url=args.system_url,
        output_dir=args.output_dir,
        assets_dir=args.assets_dir,
        languages=args.languages.split(",") if args.languages else ["en"],
        docs=args.docs.split(",") if args.docs else ["13", "15", "19"],
    )


def discover_routes(config):
    """Return merged route list across all configured frontends.

    Supports two config shapes:
      1. Legacy single-frontend via config.ROUTES (Next.js only)
      2. Multi-frontend via config.FRONTENDS = [{id, base_url, router_type, ...}]

    Every emitted route dict gains `base_url` and `frontend_id` so the capture
    step knows which host to hit and which subsystem the shot belongs to.
    """
    import discover
    frontends = getattr(config, "FRONTENDS", []) or []
    if not frontends:
        frontend_path = (config.ROUTES.get("frontend_path") if hasattr(config, "ROUTES")
                         else "frontend/app")
        ignore = config.ROUTES.get("ignore") if hasattr(config, "ROUTES") else None
        routes = discover.walk(config.LOCAL_REPO, frontend_path, ignore)
        for r in routes:
            r.setdefault("base_url", config.SYSTEM_URL)
            r.setdefault("frontend_id", "default")
        return routes

    merged = []
    for fe in frontends:
        fe_id = fe.get("id", "")
        base_url = fe.get("base_url", config.SYSTEM_URL)
        repo = fe.get("repo") or config.LOCAL_REPO
        router_type = fe.get("router_type", "nextjs")
        prefix = fe.get("prefix", fe_id)
        i18n_mode = fe.get("i18n_mode", "locale_segment")
        login_path = fe.get("login_path", "")
        if router_type == "vue":
            router_file = fe.get("router_file", "src/router/index.js")
            routes = discover.walk_vue(repo, router_file, prefix=prefix)
        elif router_type == "static":
            static = fe.get("static_routes", []) or []
            routes = []
            for s in static:
                route = s["route"]
                slug = s.get("id_slug") or (
                    route.strip("/").replace("/", "-").replace(".", "-") or "home"
                )
                pid_prefix = f"FE-{prefix}-" if prefix else "FE-"
                routes.append({
                    "id": f"{pid_prefix}{slug}",
                    "route": route,
                    "is_dynamic": False,
                    "title_guess": s.get("title") or slug.replace("-", " ").title(),
                })
        else:
            frontend_path = fe.get("frontend_path", "frontend/app")
            ignore = fe.get("ignore")
            routes = discover.walk(repo, frontend_path, ignore)
            if prefix:
                for r in routes:
                    r["id"] = r["id"].replace("FE-", f"FE-{prefix}-", 1)

        keep_prefixes = fe.get("keep_route_prefixes") or []
        drop_prefixes = fe.get("drop_route_prefixes") or []
        if keep_prefixes:
            routes = [r for r in routes
                      if any(r["route"].startswith(p) for p in keep_prefixes)]
        if drop_prefixes:
            routes = [r for r in routes
                      if not any(r["route"].startswith(p) for p in drop_prefixes)]

        for r in routes:
            r["base_url"] = base_url
            r["frontend_id"] = fe_id
            r["i18n_mode"] = i18n_mode
            r["login_path"] = login_path
        print(f"  [discover] {fe_id}: {len(routes)} routes ({router_type})")
        merged.extend(routes)
    return merged


def wipe_output(config):
    """Delete prior .docx and assets/ from output dir."""
    if not os.path.isdir(config.OUTPUT_DIR):
        return
    for f in os.listdir(config.OUTPUT_DIR):
        full = os.path.join(config.OUTPUT_DIR, f)
        if f.endswith(".docx"):
            os.remove(full)
            print(f"  [fresh] removed {f}")
    if os.path.isdir(config.ASSETS_DIR):
        shutil.rmtree(config.ASSETS_DIR)
        print(f"  [fresh] removed assets/")
    os.makedirs(config.DIAGRAMS_DIR, exist_ok=True)
    os.makedirs(config.SCREENSHOTS_DIR, exist_ok=True)


def main():
    args = parse_args()
    config = build_config(args)
    analysis, get_analysis = load_analysis(args.analysis_file)

    print("=" * 60)
    print(f"ISO Document Generator — {config.PROJECT_NAME}")
    print(f"Code: {config.PROJECT_CODE} | Date: {config.DOC_DATE}")
    print(f"Docs: {config.DOCS} | Languages: {config.LANGUAGES}")
    print(f"Output: {config.OUTPUT_DIR}")
    print("=" * 60)

    if args.fresh:
        print("\n[fresh] Wiping output dir...")
        wipe_output(config)

    # Sync diagrams into assets/diagrams/ automatically when the config
    # declares a source — explicit --diagrams flag also forces a sync.
    auto_src = args.diagrams_src or getattr(config, "DIAGRAMS_SOURCE", "")
    if args.diagrams or auto_src:
        import diagrams
        src = args.diagrams_src or auto_src
        if src:
            print(f"\n[diagrams] syncing {src} -> {config.DIAGRAMS_DIR}")
            diagrams.sync(src, config.DIAGRAMS_DIR, force=args.diagrams)

    if args.capture:
        import capture
        import discover
        routes = discover_routes(config)
        print(f"\n[capture] discovered {len(routes)} routes")
        for lang in config.LANGUAGES:
            print(f"\n[capture] === {lang.upper()} ===")
            capture.capture_routes(config, routes, lang, skip_login=args.skip_login)

    results = []
    builders = {"13": doc13.build, "15": doc15.build, "19": doc19.build}

    for lang in config.LANGUAGES:
        a = get_analysis(lang) if get_analysis else analysis
        for doc_type in config.DOCS:
            builder = builders.get(doc_type)
            if not builder:
                continue
            label = {"13": "Software Components", "15": "Software Design",
                     "19": "Test Report"}.get(doc_type, doc_type)
            print(f"\n[{lang}] Generating {label} (#{doc_type})...")
            results.append(builder(config, a, lang=lang))

    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    for r in results:
        size = os.path.getsize(r) / 1024
        print(f"  {os.path.basename(r)} ({size:.0f} KB)")
    print("\nDone!")


if __name__ == "__main__":
    main()
