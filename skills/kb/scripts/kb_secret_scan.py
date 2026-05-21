#!/usr/bin/env python3
"""Secret scanner for the /kb skill.

CLI:
    echo '{"chunks":[{"idx":0,"body":"..."}]}' | \\
        python3 kb_secret_scan.py --patterns <path-to-secret-patterns.json>

Returns JSON on stdout: {"rejected": [{"idx": N, "reason": "<rule>"}]}

Rejects (never redacts) any chunk that:
- matches one of the regex patterns in --patterns
- contains an env-style KEY=value where the value clears the entropy bar
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def scan_one(body: str, patterns_data: dict[str, Any]) -> str | None:
    """Return a rejection reason string, or None if clean."""
    # 1) Regex patterns
    for p in patterns_data.get("patterns", []):
        if re.search(p["regex"], body):
            return p["name"]

    # 2) Env-style KEY=value with high-entropy value
    envstyle = patterns_data.get("envstyle")
    if envstyle:
        rx = re.compile(envstyle["key_value_regex"])
        threshold = envstyle["shannon_threshold"]
        for m in rx.finditer(body):
            value = m.group(1)
            if shannon_entropy(value) >= threshold:
                return "envstyle_high_entropy"

    return None


def scan_chunks(chunks: list[dict[str, Any]], patterns_data: dict[str, Any]) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for chunk in chunks:
        reason = scan_one(chunk["body"], patterns_data)
        if reason is not None:
            rejected.append({"idx": chunk["idx"], "reason": reason})
    return rejected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patterns", required=True, help="Path to secret-patterns.json")
    args = ap.parse_args()

    patterns_data = json.loads(Path(args.patterns).read_text(encoding="utf-8"))
    payload = json.loads(sys.stdin.read())
    rejected = scan_chunks(payload["chunks"], patterns_data)
    json.dump({"rejected": rejected}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
