"""Render Mermaid diagrams to PNG, skipping ones whose source hasn't changed.

Usage:
    python3 diagrams.py <src_dir> <dst_dir> [--all]

Drift detection:
    For each foo.mermaid in src_dir, if foo.png in dst_dir is newer than
    foo.mermaid, skip. Else re-render with `mmdc`. With --all, force re-render.

Requires: mmdc (mermaid-cli) on PATH.
"""

import argparse
import os
import shutil
import subprocess
import sys


def find_mmdc():
    path = shutil.which("mmdc")
    if not path:
        # common install location
        for p in ("/home/bjgdr/.linuxbrew/bin/mmdc",
                  "/usr/local/bin/mmdc",
                  "/usr/bin/mmdc"):
            if os.path.exists(p):
                return p
    return path


def render(src, dst, mmdc_bin, width=1200):
    cmd = [mmdc_bin, "-i", src, "-o", dst, "-w", str(width), "-b", "transparent"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return res.returncode == 0, res.stderr


def sync(src_dir, dst_dir, force=False):
    mmdc_bin = find_mmdc()
    if not mmdc_bin:
        print("  [diagrams] mmdc not found; skipping render. Install with: npm install -g @mermaid-js/mermaid-cli")
        # Still copy existing PNGs if any
        if os.path.isdir(src_dir):
            os.makedirs(dst_dir, exist_ok=True)
            for f in os.listdir(src_dir):
                if f.endswith(".png"):
                    shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
        return

    if not os.path.isdir(src_dir):
        print(f"  [diagrams] source not found: {src_dir}")
        return
    os.makedirs(dst_dir, exist_ok=True)

    rendered, skipped = 0, 0
    for f in sorted(os.listdir(src_dir)):
        if not f.endswith(".mermaid"):
            # copy existing PNG through
            if f.endswith(".png"):
                shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
            continue

        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f.replace(".mermaid", ".png"))

        if not force and os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            skipped += 1
            continue

        ok, err = render(src, dst, mmdc_bin)
        if ok:
            rendered += 1
            print(f"  [diagrams] rendered {f}")
        else:
            print(f"  [diagrams] FAIL {f}: {err.strip()[:200]}")

    print(f"  [diagrams] rendered={rendered} skipped={skipped}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src_dir")
    parser.add_argument("dst_dir")
    parser.add_argument("--all", action="store_true", help="force re-render")
    args = parser.parse_args()
    sync(args.src_dir, args.dst_dir, force=args.all)


if __name__ == "__main__":
    main()
