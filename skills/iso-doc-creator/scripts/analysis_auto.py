"""
analysis_auto.py — pipeline v2 shim.

Reads analysis.json (produced by jira-fetch pipeline v2) and exposes it as the
`analysis` dict that doc13/doc15/doc19 builders consume.

Usage from run.py:
  python3 run.py \\
    --config-file /path/to/iso-doc.json \\
    --analysis-file /path/to/analysis_auto.py

Set PIPELINE_ANALYSIS_JSON env var to override the analysis.json location.
Defaults to analysis.json next to this script.

Schema: see packages/shared/src/analysis-schema.ts (AnalysisJson) in jira-fetch.
"""

import json
import os
from pathlib import Path

_path = os.environ.get(
    "PIPELINE_ANALYSIS_JSON",
    str(Path(__file__).parent / "analysis.json"),
)

try:
    with open(_path, "r", encoding="utf-8") as _f:
        _data = json.load(_f)
except FileNotFoundError:
    print(f"[analysis_auto] WARN: {_path} not found — analysis will be empty")
    _data = {"schema_version": "1.0", "sections": {}}

_schema_version = _data.get("schema_version")
if _schema_version != "1.0":
    print(
        f"[analysis_auto] WARN: unknown schema_version {_schema_version!r}; "
        f"using best-effort flatten"
    )

# Flatten sections → analysis dict. Skip "absent" sections so the skill falls
# back to its default text for those.
analysis = {}
for _key, _section in (_data.get("sections") or {}).items():
    if _section and _section.get("source") != "absent":
        analysis[_key] = _section.get("data")


_BILINGUAL_KEYS = {
    "description",
    "frontend_intro",
    "data_protection",
    "test_scope",
    "test_strategy",
    "test_summary",
    "coverage_gaps",
    "defect_summary",
}


def get_analysis(lang: str):
    """
    Called by run.py per language. Bilingual fields are resolved by `lang`;
    non-bilingual rows (table tuples) pass through unchanged so the doc
    builders see the same shapes they see from hand-curated analysis_*.py.
    """
    result = {}
    for key, val in analysis.items():
        if key in _BILINGUAL_KEYS and isinstance(val, dict) and lang in val:
            result[key] = val[lang]
        else:
            result[key] = val
    return result
