#!/usr/bin/env python3
"""Seed an SSOT KG from a UA Impl KG.

One-shot bootstrap. Reads an existing Impl KG (produced by the `understand`
skill), copies its structure verbatim, adds SSOT defaults to every node, edge,
and layer, and writes the result alongside config.json + meta.json.

Reads:
  <impl>                                # Impl KG (default: .understand-anything/knowledge-graph.json)
  <impl-meta>                           # Impl meta.json (sibling of <impl>)

Writes:
  <out>                                 # SSOT KG (default: .understand-anything-ssot/knowledge-graph.json)
  <out-dir>/config.json                 # {"autoUpdate": false}
  <out-dir>/meta.json                   # bootstrap metadata

Usage:
  python3 scripts/ssot_seed.py
  python3 scripts/ssot_seed.py --impl <path> --out <path>
  python3 scripts/ssot_seed.py --force      # overwrite existing SSOT KG
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


def _load_json(p: Path) -> dict:
    if not p.exists():
        sys.stderr.write(f"missing: {p}\n")
        sys.exit(2)
    return json.loads(p.read_text())


def _apply_defaults(obj: dict, defaults: dict) -> None:
    for k, v in defaults.items():
        obj.setdefault(k, list(v) if isinstance(v, list) else v)


def seed(impl: dict, impl_meta: dict) -> dict:
    g = copy.deepcopy(impl)
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


def _meta(g: dict) -> dict:
    return {
        "ssot_version": "1.0.0",
        "seeded_from_ua_commit": g.get("ssot_seeded_from"),
        "seeded_at": g.get("ssot_seeded_at"),
        "node_count": len(g.get("nodes", [])),
        "edge_count": len(g.get("edges", [])),
        "layer_count": len(g.get("layers", [])),
        "confirmed_nodes": 0,
        "confirmed_layers": 0,
    }


def main() -> int:
    repo = Path.cwd()
    default_impl = repo / ".understand-anything" / "knowledge-graph.json"
    default_out = repo / ".understand-anything-ssot" / "knowledge-graph.json"

    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", type=Path, default=default_impl,
                    help="path to Impl KG knowledge-graph.json")
    ap.add_argument("--out", type=Path, default=default_out,
                    help="path to write the SSOT KG")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing SSOT KG")
    args = ap.parse_args()

    if args.out.exists() and not args.force:
        sys.stderr.write(
            f"refusing to overwrite existing {args.out} (use --force)\n"
        )
        return 1

    impl_meta_path = args.impl.parent / "meta.json"
    impl = _load_json(args.impl)
    impl_meta = _load_json(impl_meta_path) if impl_meta_path.exists() else {}

    g = seed(impl, impl_meta)
    meta = _meta(g)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n")
    (args.out.parent / "config.json").write_text(
        json.dumps({"autoUpdate": False}) + "\n"
    )
    (args.out.parent / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    print(f"seeded {args.out}")
    print(
        f"  nodes={meta['node_count']} edges={meta['edge_count']} "
        f"layers={meta['layer_count']} "
        f"from_commit={meta['seeded_from_ua_commit']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
