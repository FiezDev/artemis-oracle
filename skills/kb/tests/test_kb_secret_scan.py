"""Tests for kb_secret_scan. Use a temp patterns file to keep the tests
hermetic and decoupled from any future tweaks to the shipped patterns."""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "kb_secret_scan.py"
DEFAULT_PATTERNS = Path(__file__).parent.parent / "secret-patterns.json"


def _import_module():
    sys.modules.pop("kb_secret_scan", None)
    spec = importlib.util.spec_from_file_location("kb_secret_scan", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_cli(stdin_payload: str, patterns_path: Path = DEFAULT_PATTERNS) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--patterns", str(patterns_path)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_aws_access_key_is_rejected():
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": "creds: AKIAIOSFODNN7EXAMPLE in code"}]}))
    rejected = out["rejected"]
    assert len(rejected) == 1
    assert rejected[0]["idx"] == 0
    assert "aws" in rejected[0]["reason"].lower()


def test_github_pat_classic_is_rejected():
    body = "token=ghp_" + "x" * 36
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0
    assert "github" in out["rejected"][0]["reason"].lower()


def test_jwt_shaped_is_rejected():
    body = "Bearer eyJabcdefghij.eyJklmnopqrst.uvwxyz12345abcdef"
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0


def test_pem_private_key_is_rejected():
    body = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAxxxxx\n-----END RSA PRIVATE KEY-----"
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0
    assert "private_key" in out["rejected"][0]["reason"].lower()


def test_envstyle_high_entropy_value_is_rejected():
    body = "Found in config: API_TOKEN=Z9mvX4LpQ7nRf2YbV0aS6hKjEcOiTu1wN3"
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"][0]["idx"] == 0


def test_clean_prose_is_accepted():
    body = "The new rice variety RD43 tolerates monsoon lodging better than RD41."
    out = _run_cli(json.dumps({"chunks": [{"idx": 0, "body": body}]}))
    assert out["rejected"] == []


def test_multiple_chunks_return_indexed_rejects():
    payload = json.dumps({
        "chunks": [
            {"idx": 0, "body": "clean prose about rice"},
            {"idx": 1, "body": "AKIAIOSFODNN7EXAMPLE leaked"},
            {"idx": 2, "body": "more clean prose"},
            {"idx": 3, "body": "another with ghp_" + "y" * 36},
        ],
    })
    out = _run_cli(payload)
    idxs = sorted(r["idx"] for r in out["rejected"])
    assert idxs == [1, 3]


def test_shannon_entropy_function():
    m = _import_module()
    # Known: 8 unique chars equally distributed → 3 bits.
    s = "abcdefgh" * 4
    e = m.shannon_entropy(s)
    assert 2.9 < e < 3.1
    # All same char → 0 entropy.
    assert m.shannon_entropy("aaaaaaaaaaaa") == 0.0
