# SSOT Knowledge Graph

Parallel to `.understand-anything/` (Impl KG, `autoUpdate=true`, derived from source).

This KG represents **intent** — what the code should be, not what it is. It is a **projection** of the Decision Log at `docs/ssot/decisions/index.jsonl`.

## Files

- `knowledge-graph.json` — same schema as the UA Impl KG, plus 5 SSOT fields per node (and SSOT fields per edge / layer).
- `config.json` — `{"autoUpdate": false}` (SSOT never auto-updates from code).
- `meta.json` — bootstrap metadata (seed source commit, counts, confirmed counters).
- `schema.md` — SSOT-specific field documentation.

## SSOT node fields (on top of UA schema)

- `status`: `inherited | confirmed | spec | wip | implemented | drift | deprecated`
- `acceptance`: behavioral spec (natural language or Gherkin). Seeds tests.
- `contract`: input/output types, error modes, invariants.
- `rationale_ref`: list of Decision Log entry IDs (`DL-YYYY-MM-DD-NNN`).
- `touch_budget`: list of file globs implementations are allowed to touch.

## SSOT edge fields

- `status`: `inherited | confirmed | spec | implemented | drift | deprecated`
- `rationale_ref`: list of DL IDs.

## SSOT layer fields

- `status`: `inherited | confirmed | spec | implemented | drift | deprecated`
- `acceptance`: layer-wide invariant.
- `rationale_ref`: list of DL IDs.

## Editing rules

**Never edit `knowledge-graph.json` directly.** All mutations flow through the Decision Log:

1. Append a `DL-YYYY-MM-DD-NNN` entry to `docs/ssot/decisions/index.jsonl`.
2. Run `python3 scripts/ssot_replay.py` to rebuild this file.
3. Run `python3 scripts/ssot_diff.py` to see drift vs Impl.

Replay is idempotent — running it twice produces an identical KG.

See `docs/ssot/decisions/README.md` for the full effect grammar.
