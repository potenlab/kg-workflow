#!/usr/bin/env python3
"""Diff Impl KG vs SSOT KG.

Default paths (run from repo root):
  .understand-anything/knowledge-graph.json        (Impl)
  .understand-anything-ssot/knowledge-graph.json   (SSOT)

Reports six buckets:
  - missing_in_impl         : SSOT has node, Impl does not
  - extra_in_impl           : Impl has node, SSOT does not
  - signature_drift         : same id, mismatched type/name/filePath
  - acceptance_missing      : SSOT node confirmed but acceptance is null
  - missing_edges_in_impl   : SSOT has edge, Impl does not
  - extra_edges_in_impl     : Impl has edge, SSOT does not

Exit codes:
  0  : no findings
  1  : drift found (non-zero in CI gate)
  2  : usage / IO error

Usage:
  python3 scripts/ssot_diff.py                    # summary
  python3 scripts/ssot_diff.py --json             # machine-readable
  python3 scripts/ssot_diff.py --acceptance-only  # only flag acceptance_missing
  python3 scripts/ssot_diff.py --impl <path> --ssot <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SIGNATURE_FIELDS = ("type", "name", "filePath")


def _load(p: Path) -> dict:
    if not p.exists():
        sys.stderr.write(f"missing: {p}\n")
        sys.exit(2)
    return json.loads(p.read_text())


def _edge_key(e: dict) -> tuple:
    return (e["source"], e["target"], e["type"])


def diff(impl: dict, ssot: dict) -> dict:
    impl_nodes = {n["id"]: n for n in impl.get("nodes", [])}
    ssot_nodes = {n["id"]: n for n in ssot.get("nodes", [])}
    impl_edges = {_edge_key(e): e for e in impl.get("edges", [])}
    ssot_edges = {_edge_key(e): e for e in ssot.get("edges", [])}

    findings: dict[str, list] = {
        "missing_in_impl": [],
        "extra_in_impl": [],
        "signature_drift": [],
        "acceptance_missing": [],
        "missing_edges_in_impl": [],
        "extra_edges_in_impl": [],
    }

    for nid, snode in ssot_nodes.items():
        if snode.get("status") == "deprecated":
            continue
        if nid not in impl_nodes:
            findings["missing_in_impl"].append({
                "id": nid,
                "status": snode.get("status"),
                "name": snode.get("name"),
            })
            continue
        inode = impl_nodes[nid]
        delta = {
            f: (snode.get(f), inode.get(f))
            for f in SIGNATURE_FIELDS
            if snode.get(f) != inode.get(f)
        }
        if delta:
            findings["signature_drift"].append({"id": nid, "delta": delta})

    for nid in impl_nodes.keys() - ssot_nodes.keys():
        findings["extra_in_impl"].append({"id": nid})

    for nid, snode in ssot_nodes.items():
        if snode.get("status") == "confirmed" and snode.get("acceptance") in (None, ""):
            findings["acceptance_missing"].append({"id": nid})

    for k in ssot_edges.keys() - impl_edges.keys():
        findings["missing_edges_in_impl"].append(
            {"source": k[0], "target": k[1], "type": k[2]}
        )
    for k in impl_edges.keys() - ssot_edges.keys():
        findings["extra_edges_in_impl"].append(
            {"source": k[0], "target": k[1], "type": k[2]}
        )

    return findings


def _summarize(findings: dict) -> str:
    return "\n".join(f"  {k:24s} {len(v)}" for k, v in findings.items())


def main() -> int:
    repo = Path.cwd()
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", type=Path,
                    default=repo / ".understand-anything" / "knowledge-graph.json")
    ap.add_argument("--ssot", type=Path,
                    default=repo / ".understand-anything-ssot" / "knowledge-graph.json")
    ap.add_argument("--json", action="store_true", help="emit findings JSON")
    ap.add_argument("--acceptance-only", action="store_true",
                    help="only flag acceptance_missing (other buckets ignored for exit code)")
    args = ap.parse_args()

    impl = _load(args.impl)
    ssot = _load(args.ssot)
    findings = diff(impl, ssot)

    if args.json:
        json.dump(findings, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("SSOT drift report")
        print(_summarize(findings))

    if args.acceptance_only:
        return 1 if findings["acceptance_missing"] else 0

    total = sum(len(v) for v in findings.values())
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
