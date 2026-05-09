#!/usr/bin/env python3
"""
Publish or schedule posts to a Facebook Page via Graph API v23.0.

Reads JSON from stdin:
  {
    "text": "<post body>",
    "images": ["/path/a.jpg", "/path/b.jpg"]   // optional
    "pageId": "<id>",                          // optional, default AI Inspire
    "dripIntervalHours": 3,                    // optional, null = post now
    "dripStartOffsetMinutes": 10,              // optional, default 10
    "dripBaseAt": "2026-04-27T09:00:00+07:00", // optional
    "iterationIndex": 0,                       // 0-based
    "tokenPath": "/tmp/page-token.txt"         // optional
  }

Emits JSON to stdout:
  {"ok": true, "postId": "...", "scheduled": true, "scheduledAt": "...", "url": "..."}

Failures emit {"ok": false, "error": "..."} with exit 1.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
import ssl
from urllib import request as urlreq, parse as urlparse, error as urlerr

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")

GRAPH = "https://graph.facebook.com/v23.0"
DEFAULT_PAGE = "1136813799507714"
DEFAULT_TOKEN_PATH = "/tmp/page-token.txt"
MIN_LEAD_SECONDS = 10 * 60
MAX_LEAD_SECONDS = 75 * 24 * 3600


def die(msg):
    print(json.dumps({"ok": False, "error": msg}))
    sys.exit(1)


def read_token(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError as e:
        die(f"cannot read token at {path}: {e}")


def parse_iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception as e:
        die(f"invalid ISO timestamp {s!r}: {e}")


def schedule_for(payload, now_unix):
    drip = payload.get("dripIntervalHours")
    if drip in (None, "", 0):
        return None
    offset_min = int(payload.get("dripStartOffsetMinutes") or 10)
    base_at = payload.get("dripBaseAt")
    if base_at:
        base = int(parse_iso(base_at).timestamp())
    else:
        base = now_unix
    idx = int(payload.get("iterationIndex") or 0)
    sched = base + (offset_min * 60) + int(idx * float(drip) * 3600)
    if sched < now_unix + MIN_LEAD_SECONDS:
        die(f"scheduled time {sched} is < 10 min in the future (now={now_unix})")
    if sched > now_unix + MAX_LEAD_SECONDS:
        die(f"scheduled time {sched} is > 75 days in the future")
    return sched


def post_form(url, fields, files=None):
    """POST form data, optionally with a file. Returns parsed JSON."""
    if files:
        # multipart for file uploads
        boundary = f"----qone{int(time.time()*1000)}"
        body = bytearray()
        for k, v in fields.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
            body += str(v).encode()
            body += b"\r\n"
        for fkey, fpath in files.items():
            fname = os.path.basename(fpath)
            with open(fpath, "rb") as fh:
                content = fh.read()
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{fkey}"; filename="{fname}"\r\n'.encode()
            body += b"Content-Type: application/octet-stream\r\n\r\n"
            body += content
            body += b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urlreq.Request(url, data=bytes(body), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    else:
        data = urlparse.urlencode(fields).encode()
        req = urlreq.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        resp = urlreq.urlopen(req, timeout=120, context=SSL_CTX)
        return json.loads(resp.read().decode())
    except urlerr.HTTPError as e:
        body = e.read().decode(errors="replace")
        die(f"HTTP {e.code} from {url}: {body}")
    except Exception as e:
        die(f"request to {url} failed: {e}")


def upload_unpublished_photo(page_id, image_path, token):
    fields = {"published": "false", "temporary": "true", "access_token": token}
    res = post_form(f"{GRAPH}/{page_id}/photos", fields, files={"source": image_path})
    if "id" not in res:
        die(f"photo upload missing id: {res}")
    return res["id"]


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        die("no JSON on stdin")
    try:
        p = json.loads(raw)
    except Exception as e:
        die(f"invalid JSON on stdin: {e}")

    text = p.get("text")
    if not text:
        die("'text' is required")

    page_id = p.get("pageId") or DEFAULT_PAGE
    token_path = p.get("tokenPath") or os.environ.get("PAGE_TOKEN_PATH") or DEFAULT_TOKEN_PATH
    token = os.environ.get("PAGE_TOKEN") or read_token(token_path)

    images = p.get("images") or []
    if isinstance(images, str):
        images = [images] if images else []

    now = int(time.time())
    sched = schedule_for(p, now)

    schedule_fields = {}
    if sched is not None:
        schedule_fields["published"] = "false"
        schedule_fields["scheduled_publish_time"] = str(sched)
    else:
        schedule_fields["published"] = "true"

    if images:
        media_ids = [upload_unpublished_photo(page_id, img, token) for img in images]
        fields = {"message": text, "access_token": token, **schedule_fields}
        for i, mid in enumerate(media_ids):
            fields[f"attached_media[{i}]"] = json.dumps({"media_fbid": mid})
        res = post_form(f"{GRAPH}/{page_id}/feed", fields)
        post_id = res.get("id")
    else:
        fields = {"message": text, "access_token": token, **schedule_fields}
        res = post_form(f"{GRAPH}/{page_id}/feed", fields)
        post_id = res.get("id")

    if not post_id:
        die(f"post returned no id: {res}")

    sched_iso = (
        datetime.fromtimestamp(sched, tz=timezone.utc).isoformat() if sched is not None else None
    )
    out = {
        "ok": True,
        "postId": post_id,
        "scheduled": sched is not None,
        "scheduledAt": sched_iso,
        "url": f"https://facebook.com/{post_id}",
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
