# SSOT Knowledge Graph

Parallel to `.understand-anything/` (Impl KG, `autoUpdate=true`, derived from source).

This KG represents **intent** — what the code should be, not what it is. It was seeded once by [kg-workflow](https://github.com/potenlab/kg-workflow)'s `/kg-init` from the Impl KG at seed time.

## Files

- `knowledge-graph.json` — same schema as the UA Impl KG, plus 5 SSOT fields per node (and SSOT fields per edge / layer).
- `config.json` — `{"autoUpdate": false}` (SSOT never auto-updates from code).
- `meta.json` — bootstrap metadata (seed source commit, counts, confirmed counters).
- `schema.md` — SSOT-specific field documentation.

## SSOT node fields (on top of UA schema)

- `status`: `inherited | confirmed | spec | wip | implemented | drift | deprecated`
- `acceptance`: behavioral spec (natural language or Gherkin). Seeds tests.
- `contract`: input/output types, error modes, invariants.
- `rationale_ref`: list of references explaining why the field is what it is (free-form — e.g. ticket IDs, doc links, ADR IDs).
- `touch_budget`: list of file globs implementations are allowed to touch.

## SSOT edge fields

- `status`: `inherited | confirmed | spec | implemented | drift | deprecated`
- `rationale_ref`: list of references.

## SSOT layer fields

- `status`: `inherited | confirmed | spec | implemented | drift | deprecated`
- `acceptance`: layer-wide invariant.
- `rationale_ref`: list of references.

## How SSOT is mutated

**Not defined by kg-workflow.** Pick a process that fits this repo:

- An append-only Decision Log with a deterministic replay script (recommended for teams).
- Hand-edits to `knowledge-graph.json` reviewed via normal code review.
- A separate workflow tool you bring yourself.

Whatever you pick, document it here and follow it consistently. The fields above are stable; the process is yours to choose.
