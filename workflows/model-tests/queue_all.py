#!/usr/bin/env python3
"""Submit workflows to ComfyUI queue without waiting; record prompt_ids."""
import json, sys, time, urllib.request, urllib.error, uuid, pathlib

API = "http://localhost:8188"

def submit(path):
    wf = json.loads(pathlib.Path(path).read_text())
    req = urllib.request.Request(f"{API}/prompt",
        data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        return {"path": path, "prompt_id": r.get("prompt_id"), "error": None}
    except urllib.error.HTTPError as e:
        return {"path": path, "prompt_id": None, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"path": path, "prompt_id": None, "error": str(e)[:500]}

if __name__ == "__main__":
    results = []
    for p in sys.argv[1:]:
        r = submit(p)
        print(f"{'OK' if r['prompt_id'] else 'FAIL'} {p} -> {r['prompt_id'] or r['error'][:120]}")
        results.append(r)
    # Save manifest
    manifest = pathlib.Path(__file__).parent / "results" / f"queue_{int(time.time())}.json"
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps(results, indent=2))
    print(f"manifest: {manifest}")
