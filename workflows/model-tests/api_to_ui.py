#!/usr/bin/env python3
"""Convert ComfyUI API-format prompt JSON to UI graph format.

Fetches each node's schema from the running ComfyUI (/object_info) so widget
order and I/O typing match what the frontend expects. Auto-lays out nodes
by topological-sort depth.
"""
import json, sys, urllib.request, pathlib, re

API = "http://localhost:8188"

def fetch_object_info():
    return json.loads(urllib.request.urlopen(f"{API}/object_info", timeout=30).read())

def inputs_of(schema, node_class):
    s = schema.get(node_class, {}).get("input", {})
    order = s.get("input_order", {}).get("required", []) + s.get("input_order", {}).get("optional", [])
    req = s.get("required", {})
    opt = s.get("optional", {})
    merged = []
    seen = set()
    for k in order:
        if k in req: merged.append((k, req[k], True)); seen.add(k)
        elif k in opt: merged.append((k, opt[k], False)); seen.add(k)
    for k, v in req.items():
        if k not in seen: merged.append((k, v, True))
    for k, v in opt.items():
        if k not in seen: merged.append((k, v, False))
    return merged

def outputs_of(schema, node_class):
    s = schema.get(node_class, {})
    out_types = s.get("output", [])
    out_names = s.get("output_name", []) or [t for t in out_types]
    return list(zip(out_types, out_names))

def is_slot_type(type_spec):
    """A field is a link slot (not a widget) if its type is not a primitive/combo."""
    t = type_spec[0]
    if isinstance(t, list):
        return False  # COMBO dropdown -> widget
    return t not in ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO")

def convert(api_wf, schema):
    # Topo sort for layout
    deps = {nid: set() for nid in api_wf}
    for nid, node in api_wf.items():
        for k, v in node.get("inputs", {}).items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                deps[nid].add(v[0])
    depth = {}
    def d(nid):
        if nid in depth: return depth[nid]
        depth[nid] = 0 if not deps[nid] else 1 + max(d(x) for x in deps[nid])
        return depth[nid]
    for nid in api_wf: d(nid)
    # Group by depth column
    by_col = {}
    for nid, col in depth.items():
        by_col.setdefault(col, []).append(nid)
    # Position
    X_STEP, Y_STEP, X0, Y0 = 360, 180, 100, 100
    pos = {}
    for col, nids in by_col.items():
        for i, nid in enumerate(sorted(nids, key=int)):
            pos[nid] = [X0 + col * X_STEP, Y0 + i * Y_STEP]

    nodes = []
    links = []  # [link_id, from_node, from_slot, to_node, to_slot, type]
    link_id = 0
    # Preassign integer node ids (same as string keys)
    order = sorted(api_wf.keys(), key=int)
    for i, nid in enumerate(order):
        node = api_wf[nid]
        cls = node["class_type"]
        title = node.get("_meta", {}).get("title", cls)
        sch_inputs = inputs_of(schema, cls)
        sch_outputs = outputs_of(schema, cls)

        node_inputs = []
        widgets_values = []
        for name, spec, required in sch_inputs:
            if is_slot_type(spec):
                supplied = node.get("inputs", {}).get(name)
                link = None
                if isinstance(supplied, list) and len(supplied) == 2 and isinstance(supplied[0], str):
                    pass  # link recorded later
                node_inputs.append({"name": name, "type": spec[0], "link": None})
            else:
                val = node.get("inputs", {}).get(name)
                if val is None and isinstance(spec[1], dict) and "default" in spec[1]:
                    val = spec[1]["default"]
                if val is None and isinstance(spec[0], list):
                    val = spec[0][0] if spec[0] else ""
                widgets_values.append(val)

        node_outputs = []
        for j, (otype, oname) in enumerate(sch_outputs):
            node_outputs.append({"name": oname, "type": otype, "links": [], "slot_index": j})

        nodes.append({
            "id": int(nid),
            "type": cls,
            "pos": pos[nid],
            "size": [300, 120],
            "flags": {},
            "order": i,
            "mode": 0,
            "inputs": node_inputs,
            "outputs": node_outputs,
            "properties": {"Node name for S&R": cls},
            "widgets_values": widgets_values,
            "title": title,
        })

    # Build links from API connections
    for nid in order:
        node = api_wf[nid]
        cls = node["class_type"]
        slot_index_of = {n["name"]: i for i, n in enumerate(next(x for x in nodes if x["id"] == int(nid))["inputs"])}
        for k, v in node.get("inputs", {}).items():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                src_nid, src_slot = v[0], int(v[1])
                if k not in slot_index_of: continue
                dst_slot = slot_index_of[k]
                # find output type on source
                src_node = next(x for x in nodes if x["id"] == int(src_nid))
                if src_slot >= len(src_node["outputs"]): continue
                otype = src_node["outputs"][src_slot]["type"]
                link_id += 1
                links.append([link_id, int(src_nid), src_slot, int(nid), dst_slot, otype])
                # update input link ref
                dst_node = next(x for x in nodes if x["id"] == int(nid))
                dst_node["inputs"][dst_slot]["link"] = link_id
                src_node["outputs"][src_slot]["links"].append(link_id)

    return {
        "last_node_id": max(int(n) for n in order),
        "last_link_id": link_id,
        "nodes": nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }

if __name__ == "__main__":
    schema = fetch_object_info()
    for src in sys.argv[1:]:
        src = pathlib.Path(src)
        api_wf = json.loads(src.read_text())
        ui_wf = convert(api_wf, schema)
        dst = src.with_name(src.stem + "_ui.json")
        dst.write_text(json.dumps(ui_wf, indent=2))
        print(f"{src.name} -> {dst.name} ({len(ui_wf['nodes'])} nodes, {len(ui_wf['links'])} links)")
