#!/usr/bin/env python3
"""Report drift between the frozen SSOT KG and the live Impl KG.

The Impl KG (`.understand-anything/knowledge-graph.json`) auto-updates on every
commit. The SSOT KG (`.understand-anything-ssot/knowledge-graph.json`) is frozen
at seed time and mutated deliberately. Over time the two diverge — this script
makes that divergence visible.

It classifies drift into three buckets:

  - UNCOVERED   Impl nodes with no SSOT entry      (new code, no declared intent)
  - ORPHANED    SSOT nodes with no Impl entry       (intent for code that's gone)
  - MOVED        nodes in both whose filePath/type changed since seed

and highlights how much of your *curated* SSOT (nodes you marked spec/confirmed/
etc., i.e. status != inherited) is affected — that's the drift that actually
matters, vs. nodes you never reviewed.

Reads:
  <impl>   live Impl KG   (default: .understand-anything/knowledge-graph.json)
  <ssot>   frozen SSOT KG (default: .understand-anything-ssot/knowledge-graph.json)

Usage:
  python3 scripts/ssot_diff.py
  python3 scripts/ssot_diff.py --quiet          # print nothing when in sync
  python3 scripts/ssot_diff.py --max 25         # cap lines per section
  python3 scripts/ssot_diff.py --impl <p> --ssot <p>

Always exits 0 — it is a report, safe to run from a SessionStart hook.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Node field names vary across understand-anything versions; try each in order.
_NAME_KEYS = ("name", "label", "title")
_FILE_KEYS = ("filePath", "file", "path", "filepath")
_TYPE_KEYS = ("type", "kind", "category")

# SSOT statuses that mean "a human curated this node" (drift here is meaningful).
_CURATED = {"confirmed", "spec", "wip", "implemented", "drift", "deprecated"}


def _first(d: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = d.get(k)
        if v:
            return str(v)
    return None


def _nid(n: dict) -> str | None:
    v = n.get("id")
    return str(v) if v is not None else None


def _name(n: dict) -> str:
    return _first(n, _NAME_KEYS) or "?"


def _file(n: dict) -> str | None:
    return _first(n, _FILE_KEYS)


def _type(n: dict) -> str | None:
    return _first(n, _TYPE_KEYS)


def _composite(n: dict) -> str:
    return f"{_file(n) or '?'}::{_name(n)}"


def _load(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _index(nodes: list[dict], key_fn) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for n in nodes:
        k = key_fn(n)
        if k and k not in out:
            out[k] = n
    return out


def _pick_key_fn(impl_nodes: list[dict], ssot_nodes: list[dict]):
    """Use node `id` if the two graphs share enough ids; otherwise fall back to a
    filePath::name composite. understand-anything may regenerate ids on update,
    which would make an id-based diff report everything as added+removed."""
    impl_ids = {_nid(n) for n in impl_nodes if _nid(n)}
    ssot_ids = {_nid(n) for n in ssot_nodes if _nid(n)}
    if impl_ids and ssot_ids:
        overlap = len(impl_ids & ssot_ids)
        smaller = min(len(impl_ids), len(ssot_ids))
        if smaller and overlap / smaller >= 0.2:
            return _nid, "id"
    return _composite, "filePath::name"


def _short(n: dict) -> str:
    f = _file(n)
    return f"{_name(n)} ({f})" if f else _name(n)


def _emit_section(lines: list[str], title: str, items: list[str], cap: int) -> None:
    if not items:
        return
    lines.append(f"  {title} ({len(items)}):")
    for s in items[:cap]:
        lines.append(f"     - {s}")
    if len(items) > cap:
        lines.append(f"     … and {len(items) - cap} more")


def main() -> int:
    repo = Path.cwd()
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", type=Path,
                    default=repo / ".understand-anything" / "knowledge-graph.json")
    ap.add_argument("--ssot", type=Path,
                    default=repo / ".understand-anything-ssot" / "knowledge-graph.json")
    ap.add_argument("--max", type=int, default=15, help="max lines per section")
    ap.add_argument("--quiet", action="store_true",
                    help="print nothing when SSOT and Impl are in sync")
    args = ap.parse_args()

    impl = _load(args.impl)
    ssot = _load(args.ssot)
    if impl is None or ssot is None:
        # Nothing to compare — stay silent and non-fatal (hook-safe).
        return 0

    impl_nodes = impl.get("nodes", []) or []
    ssot_nodes = ssot.get("nodes", []) or []
    key_fn, key_kind = _pick_key_fn(impl_nodes, ssot_nodes)

    impl_idx = _index(impl_nodes, key_fn)
    ssot_idx = _index(ssot_nodes, key_fn)

    impl_keys = set(impl_idx)
    ssot_keys = set(ssot_idx)

    uncovered = [_short(impl_idx[k]) for k in sorted(impl_keys - ssot_keys)]
    orphaned = [_short(ssot_idx[k]) for k in sorted(ssot_keys - impl_keys)]

    moved: list[str] = []
    curated_total = 0
    curated_drifted = 0
    for k in impl_keys & ssot_keys:
        s = ssot_idx[k]
        i = impl_idx[k]
        is_curated = (s.get("status") or "inherited") in _CURATED
        if is_curated:
            curated_total += 1
        sf, if_ = _file(s), _file(i)
        st, it = _type(s), _type(i)
        changed = (sf != if_) or (st != it)
        if changed:
            detail = []
            if sf != if_:
                detail.append(f"{sf} → {if_}")
            if st != it:
                detail.append(f"type {st} → {it}")
            moved.append(f"{_name(i)}: " + "; ".join(detail))
            if is_curated:
                curated_drifted += 1

    # Also count curated SSOT nodes whose code disappeared entirely (orphaned).
    for k in ssot_keys - impl_keys:
        if (ssot_idx[k].get("status") or "inherited") in _CURATED:
            curated_total += 1
            curated_drifted += 1

    in_sync = not (uncovered or orphaned or moved)
    if in_sync:
        if args.quiet:
            return 0
        print(f"[kg-workflow] ✓ SSOT in sync with Impl "
              f"(SSOT={len(ssot_nodes)} Impl={len(impl_nodes)} nodes).")
        return 0

    # Best-effort commit context.
    ssot_meta = _load(args.ssot.parent / "meta.json") or {}
    impl_meta = _load(args.impl.parent / "meta.json") or {}
    seed_sha = ssot_meta.get("seeded_from_ua_commit")
    impl_sha = impl_meta.get("gitCommitHash")

    lines = ["[kg-workflow] ⚠ SSOT drift detected"]
    ctx = f"  SSOT nodes={len(ssot_nodes)}  Impl nodes={len(impl_nodes)}  (matched by {key_kind})"
    lines.append(ctx)
    if seed_sha or impl_sha:
        lines.append(f"  seeded from Impl@{(seed_sha or '?')[:8]}  →  Impl now @{(impl_sha or '?')[:8]}")
    if curated_total:
        lines.append(f"  curated SSOT nodes affected by drift: {curated_drifted}/{curated_total}")

    _emit_section(lines, "UNCOVERED — Impl code with no SSOT intent", uncovered, args.max)
    _emit_section(lines, "ORPHANED — SSOT intent for code that no longer exists", orphaned, args.max)
    _emit_section(lines, "MOVED — node filePath/type changed since seed", moved, args.max)

    lines.append("  → Reconcile by updating .understand-anything-ssot/ "
                 "(add intent for UNCOVERED, retire ORPHANED, re-point MOVED).")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
