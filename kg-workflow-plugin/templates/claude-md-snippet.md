<!-- kg-workflow:begin -->
## Knowledge graphs (SSOT-first, Impl-second)

This repo is bootstrapped with [kg-workflow](https://github.com/potenlab/kg-workflow). Two knowledge graphs live at the repo root:

- **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` — what the code **should be**. Projected from `docs/ssot/decisions/index.jsonl` (the real source of truth). Each node carries `status`, `acceptance`, `contract`, `rationale_ref`, and `touch_budget` on top of the UA schema. `autoUpdate: false`.
- **Impl KG** — `.understand-anything/knowledge-graph.json` — what the code **actually is**. Built and refreshed by the `understand-anything` plugin from source. `autoUpdate: true`.

### How Claude should use them

**On every code question, consult SSOT first.**

1. **SSOT first.** Open `.understand-anything-ssot/knowledge-graph.json` and look up the relevant node. Read its `acceptance` (behavioral spec), `contract` (I/O + invariants), `rationale_ref` (Decision Log entry IDs), and `touch_budget` (file globs you're allowed to edit). These define intent.
2. **Impl second.** Open `.understand-anything/knowledge-graph.json` for the same node to see what the code currently looks like — file paths, exports, dependencies.
3. **If SSOT and Impl disagree on a node, surface the drift explicitly.** Default to SSOT intent unless the user overrides. Do not silently align Impl to old assumptions.
4. **Respect `touch_budget`.** When implementing or refactoring a node, do not edit files outside its `touch_budget` globs. If you need to, stop and ask the user — that's a scope change.
5. **Tests come from `acceptance`.** When writing tests for a node, derive them from its `acceptance` field, not from your own assumptions.

### Mutating SSOT — the only allowed path

Never edit `.understand-anything-ssot/knowledge-graph.json` directly. To change SSOT:

1. Append a new entry to `docs/ssot/decisions/index.jsonl` (ID: `DL-YYYY-MM-DD-NNN`, monotonic within the day, never reuse). Optionally add a long-form markdown under `docs/ssot/decisions/entries/`.
2. Run `python3 scripts/ssot_replay.py` to rebuild the SSOT KG from the log. Replay must be idempotent.
3. Run `python3 scripts/ssot_diff.py` to see drift against Impl: `missing_in_impl`, `extra_in_impl`, `signature_drift`, `acceptance_missing`.
4. Commit the decision entry, the regenerated SSOT KG, and any related code together.

### Status semantics

Each SSOT node has a `status`:

- `inherited` — defaulted at seed time, no decision yet.
- `confirmed` — explicitly affirmed via a Decision Log entry.
- `spec` — declared intent, code does not yet match.
- `wip` — implementation in flight.
- `implemented` — code matches SSOT.
- `drift` — code diverges from SSOT (caught by `ssot_diff.py`).
- `deprecated` — slated for removal.

A node flips `spec → implemented` when the next `ssot_diff.py` run shows no drift for it.

### Before every non-trivial PR

```bash
python3 scripts/ssot_replay.py --check   # SSOT KG matches the log
python3 scripts/ssot_diff.py             # report drift; treat findings as blockers unless justified
```

See `.understand-anything-ssot/README.md` and `docs/ssot/decisions/README.md` for full details.
<!-- kg-workflow:end -->
