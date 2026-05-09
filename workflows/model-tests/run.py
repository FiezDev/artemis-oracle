#!/usr/bin/env python3
"""Submit a ComfyUI workflow (API format) to localhost:8188, poll, report outputs.

Usage:
  run.py <workflow.json> [<workflow.json> ...]
  run.py <workflow.json> --param <node_id>.<input>=<value> [--param ...]
                         [--seed N] [--prompt "text"] [--out result.json]
                         [--timeout 1800] [--api http://localhost:8188]

--param values are JSON-parsed (so 42 → int, "foo" → str, true → bool).
--seed is shorthand for setting `seed`/`noise_seed` on every node that has one.
--prompt is shorthand for overriding the first CLIPTextEncode positive prompt.
"""
import argparse, json, sys, time, urllib.request, urllib.error, uuid, pathlib, copy

def post(api, path, payload):
    req = urllib.request.Request(f"{api}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def get(api, path):
    return json.loads(urllib.request.urlopen(f"{api}{path}", timeout=30).read())

def parse_value(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw

def apply_param(wf, dotted, raw_value):
    """dotted = '<node_id>.<input_key>'; sets wf[node_id]['inputs'][input_key] = parsed value."""
    node_id, _, input_key = dotted.partition(".")
    if not node_id or not input_key:
        raise ValueError(f"--param needs <node_id>.<input>=value, got {dotted!r}")
    if node_id not in wf:
        raise KeyError(f"node {node_id!r} not in workflow (have {sorted(wf.keys())[:10]}…)")
    wf[node_id].setdefault("inputs", {})[input_key] = parse_value(raw_value)

def apply_seed(wf, seed):
    for node in wf.values():
        inp = node.get("inputs", {})
        for key in ("seed", "noise_seed"):
            if key in inp and not isinstance(inp[key], list):
                inp[key] = seed

def apply_prompt(wf, text):
    for node in wf.values():
        if node.get("class_type") == "CLIPTextEncode":
            node.setdefault("inputs", {})["text"] = text
            return
    raise KeyError("no CLIPTextEncode node found for --prompt override")

def run(api, workflow_path, overrides, seed, prompt, timeout_s):
    wf = json.loads(pathlib.Path(workflow_path).read_text())
    if seed is not None: apply_seed(wf, seed)
    if prompt is not None: apply_prompt(wf, prompt)
    for dotted, raw in overrides:
        apply_param(wf, dotted, raw)

    client_id = str(uuid.uuid4())
    try:
        r = post(api, "/prompt", {"prompt": wf, "client_id": client_id})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"FAIL validate: {body}", file=sys.stderr)
        return {"status": "validate_error", "error": body}
    pid = r["prompt_id"]
    print(f"queued prompt_id={pid}")
    start = time.time()
    while True:
        if time.time() - start > timeout_s:
            return {"status": "timeout", "prompt_id": pid}
        h = get(api, f"/history/{pid}")
        if pid in h:
            entry = h[pid]
            status = entry.get("status", {})
            if status.get("completed"):
                outputs = entry.get("outputs", {})
                files = []
                for node_id, node_out in outputs.items():
                    for kind in ("images", "gifs", "videos"):
                        for f in node_out.get(kind, []):
                            files.append((node_id, kind, f))
                return {"status": "ok", "prompt_id": pid, "files": files, "elapsed_s": round(time.time()-start,1)}
            msgs = status.get("messages", [])
            for m in msgs:
                mtype = m[0] if isinstance(m, (list, tuple)) else m.get("type")
                if mtype == "execution_error":
                    return {"status": "error", "prompt_id": pid, "messages": msgs, "elapsed_s": round(time.time()-start,1)}
            if status.get("status_str") == "error":
                return {"status": "error", "prompt_id": pid, "messages": msgs, "elapsed_s": round(time.time()-start,1)}
        time.sleep(3)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("workflows", nargs="+")
    p.add_argument("--param", action="append", default=[],
                   help="<node_id>.<input>=value, value JSON-parsed. Repeatable.")
    p.add_argument("--seed", type=int)
    p.add_argument("--prompt")
    p.add_argument("--out", help="write final result JSON here")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--api", default="http://localhost:8188")
    args = p.parse_args()

    overrides = []
    for spec in args.param:
        key, _, val = spec.partition("=")
        if not _:
            sys.exit(f"--param needs key=value, got {spec!r}")
        overrides.append((key, val))

    results = []
    for path in args.workflows:
        print(f"\n=== {path} ===")
        res = run(args.api, path, overrides, args.seed, args.prompt, args.timeout)
        print(json.dumps(res, indent=2, default=str))
        results.append({"workflow": path, **res})

    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(results, indent=2, default=str))
        print(f"\nwrote {args.out}")

if __name__ == "__main__":
    main()
