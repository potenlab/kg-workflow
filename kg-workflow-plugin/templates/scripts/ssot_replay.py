#!/usr/bin/env python3
"""Replay the Decision Log into the SSOT KG.

Idempotent: starts from a fresh seed (Impl KG + SSOT defaults), then applies
every Decision Log entry's `effects` in jsonl order.

Default paths (run from repo root):
  .understand-anything/knowledge-graph.json       (seed)
  docs/ssot/decisions/index.jsonl                 (log)
  .understand-anything-ssot/knowledge-graph.json  (projection, written)
  .understand-anything-ssot/meta.json             (refreshed counters)

Effect grammar (see docs/ssot/decisions/README.md):
  - set        : merge `fields` into target (node, edge, or layer)
  - add_node   : append `node` to nodes
  - add_edge   : append `edge` to edges
  - deprecate  : set status=deprecated on target
  - remove     : drop target

Usage:
  python3 scripts/ssot_replay.py
  python3 scripts/ssot_replay.py --dry-run
  python3 scripts/ssot_replay.py --check     # CI gate: SSOT KG must equal projection
  python3 scripts/ssot_replay.py --impl <path> --ssot <path> --log <path>
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import sys
from pathlib import Path

SSOT_NODE_DEFAULTS = {
    "status": "inherited",
    "acceptance": None,
    "contract": None,
    "rationale_ref": [],
    "touch_budget": None,
}
SSOT_EDGE_DEFAULTS = {
    "status": "inherited",
    "rationale_ref": [],
}
SSOT_LAYER_DEFAULTS = {
    "status": "inherited",
    "acceptance": None,
    "rationale_ref": [],
}

VALID_OPS = {"set", "add_node", "add_edge", "deprecate", "remove"}


def _load_json(p: Path) -> dict:
    if not p.exists():
        sys.stderr.write(f"missing: {p}\n")
        sys.exit(2)
    return json.loads(p.read_text())


def _apply_defaults(obj: dict, defaults: dict) -> None:
    for k, v in defaults.items():
        obj.setdefault(k, list(v) if isinstance(v, list) else v)


def _seed_from_impl(impl_path: Path, impl_meta_path: Path) -> dict:
    g = copy.deepcopy(_load_json(impl_path))
    impl_meta = _load_json(impl_meta_path) if impl_meta_path.exists() else {}
    for n in g.get("nodes", []):
        _apply_defaults(n, SSOT_NODE_DEFAULTS)
    for e in g.get("edges", []):
        _apply_defaults(e, SSOT_EDGE_DEFAULTS)
    for L in g.get("layers", []):
        _apply_defaults(L, SSOT_LAYER_DEFAULTS)
    g["ssot_version"] = "1.0.0"
    g["ssot_seeded_from"] = impl_meta.get("gitCommitHash")
    g["ssot_seeded_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    return g


def _index(g: dict) -> tuple[dict, dict, dict]:
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    edges = {(e["source"], e["target"], e["type"]): e for e in g.get("edges", [])}
    layers = {L["id"]: L for L in g.get("layers", [])}
    return nodes, edges, layers


def _resolve_target(effect: dict, idx: tuple[dict, dict, dict]) -> tuple[str, object]:
    nodes, edges, layers = idx
    target = effect.get("target") or {}
    if isinstance(target, dict):
        kind = target.get("kind")
        tid = target.get("id")
    else:
        kind, tid = effect.get("target_kind"), target
    if kind == "node":
        if tid not in nodes:
            raise KeyError(f"node target not found: {tid}")
        return "node", nodes[tid]
    if kind == "edge":
        key = tuple(tid) if isinstance(tid, list) else tid
        if key not in edges:
            raise KeyError(f"edge target not found: {key}")
        return "edge", edges[key]
    if kind == "layer":
        if tid not in layers:
            raise KeyError(f"layer target not found: {tid}")
        return "layer", layers[tid]
    if isinstance(tid, str):
        if tid in layers:
            return "layer", layers[tid]
        if tid in nodes:
            return "node", nodes[tid]
    raise KeyError(f"cannot resolve target for {target!r}")


def _apply_effect(effect: dict, g: dict, idx: tuple[dict, dict, dict]) -> None:
    op = effect.get("op")
    if op not in VALID_OPS:
        raise ValueError(f"unknown op: {op!r}")

    if op == "add_node":
        new = effect["node"]
        _apply_defaults(new, SSOT_NODE_DEFAULTS)
        g.setdefault("nodes", []).append(new)
        idx[0][new["id"]] = new
        return

    if op == "add_edge":
        new = effect["edge"]
        _apply_defaults(new, SSOT_EDGE_DEFAULTS)
        g.setdefault("edges", []).append(new)
        idx[1][(new["source"], new["target"], new["type"])] = new
        return

    kind, obj = _resolve_target(effect, idx)

    if op == "set":
        obj.update(effect.get("fields", {}))
        return
    if op == "deprecate":
        obj["status"] = "deprecated"
        return
    if op == "remove":
        if kind == "node":
            g["nodes"] = [n for n in g["nodes"] if n["id"] != obj["id"]]
            del idx[0][obj["id"]]
        elif kind == "edge":
            key = (obj["source"], obj["target"], obj["type"])
            g["edges"] = [
                e for e in g["edges"]
                if (e["source"], e["target"], e["type"]) != key
            ]
            del idx[1][key]
        elif kind == "layer":
            g["layers"] = [L for L in g["layers"] if L["id"] != obj["id"]]
            del idx[2][obj["id"]]
        return


def replay(impl_path: Path, impl_meta_path: Path, log_path: Path) -> tuple[dict, dict]:
    g = _seed_from_impl(impl_path, impl_meta_path)
    idx = _index(g)
    stats = {"entries": 0, "effects_applied": 0, "errors": []}

    if not log_path.exists():
        return g, stats

    for lineno, raw in enumerate(log_path.read_text().splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            stats["errors"].append(f"line {lineno}: invalid JSON: {exc}")
            continue
        stats["entries"] += 1
        for i, effect in enumerate(entry.get("effects", [])):
            try:
                _apply_effect(effect, g, idx)
                stats["effects_applied"] += 1
            except (KeyError, ValueError) as exc:
                stats["errors"].append(
                    f"{entry.get('id', f'line{lineno}')} effect[{i}]: {exc}"
                )
    return g, stats


def _meta(g: dict) -> dict:
    return {
        "ssot_version": "1.0.0",
        "seeded_from_ua_commit": g.get("ssot_seeded_from"),
        "seeded_at": g.get("ssot_seeded_at"),
        "node_count": len(g.get("nodes", [])),
        "edge_count": len(g.get("edges", [])),
        "layer_count": len(g.get("layers", [])),
        "confirmed_nodes": sum(
            1 for n in g.get("nodes", []) if n.get("status") == "confirmed"
        ),
        "confirmed_layers": sum(
            1 for L in g.get("layers", []) if L.get("status") == "confirmed"
        ),
    }


def main() -> int:
    repo = Path.cwd()
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", type=Path,
                    default=repo / ".understand-anything" / "knowledge-graph.json")
    ap.add_argument("--ssot", type=Path,
                    default=repo / ".understand-anything-ssot" / "knowledge-graph.json")
    ap.add_argument("--log", type=Path,
                    default=repo / "docs" / "ssot" / "decisions" / "index.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="fail if the replayed projection differs from the on-disk SSOT KG")
    args = ap.parse_args()

    impl_meta_path = args.impl.parent / "meta.json"
    ssot_meta_path = args.ssot.parent / "meta.json"

    g, stats = replay(args.impl, impl_meta_path, args.log)
    meta = _meta(g)

    print(f"replay: entries={stats['entries']} effects_applied={stats['effects_applied']}")
    print(
        f"  nodes={meta['node_count']} edges={meta['edge_count']} "
        f"layers={meta['layer_count']} "
        f"confirmed_nodes={meta['confirmed_nodes']} "
        f"confirmed_layers={meta['confirmed_layers']}"
    )
    if stats["errors"]:
        print("errors:")
        for e in stats["errors"]:
            print(f"  - {e}")

    if args.check:
        current = _load_json(args.ssot)
        ga = {k: v for k, v in g.items() if k != "ssot_seeded_at"}
        gb = {k: v for k, v in current.items() if k != "ssot_seeded_at"}
        if ga != gb:
            print("CHECK FAIL: replayed projection differs from on-disk SSOT KG")
            return 1
        print("CHECK OK")
        return 0

    if args.dry_run:
        return 0 if not stats["errors"] else 1

    args.ssot.parent.mkdir(parents=True, exist_ok=True)
    args.ssot.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n")
    ssot_meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {args.ssot}")
    print(f"wrote {ssot_meta_path}")
    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
