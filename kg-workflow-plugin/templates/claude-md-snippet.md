<!-- kg-workflow:begin -->
## Knowledge graphs (SSOT-first, Impl-second)

This repo is bootstrapped with [kg-workflow](https://github.com/potenlab/kg-workflow). Two knowledge graphs live at the repo root:

- **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` — what the code **should be**. Each node carries `status`, `acceptance`, `contract`, `rationale_ref`, and `touch_budget` on top of the UA schema. `autoUpdate: false`.
- **Impl KG** — `.understand-anything/knowledge-graph.json` — what the code **actually is**. Built and refreshed by the `understand-anything` plugin from source. `autoUpdate: true`.

### How Claude should use them

**On every code question, consult SSOT first.**

1. **SSOT first.** Open `.understand-anything-ssot/knowledge-graph.json` and look up the relevant node. Read its `acceptance` (behavioral spec), `contract` (I/O + invariants), `rationale_ref` (reasons / external references), and `touch_budget` (file globs you're allowed to edit). These define intent.
2. **Impl second.** Open `.understand-anything/knowledge-graph.json` for the same node to see what the code currently looks like — file paths, exports, dependencies.
3. **If SSOT and Impl disagree on a node, surface the drift explicitly.** Default to SSOT intent unless the user overrides. Do not silently align Impl to old assumptions.
4. **Respect `touch_budget`.** When implementing or refactoring a node, do not edit files outside its `touch_budget` globs. If you need to, stop and ask the user — that's a scope change.
5. **Tests come from `acceptance`.** When writing tests for a node, derive them from its `acceptance` field, not from your own assumptions.

### Status semantics

Each SSOT node has a `status`:

- `inherited` — defaulted at seed time, no decision yet.
- `confirmed` — explicitly affirmed.
- `spec` — declared intent, code does not yet match.
- `wip` — implementation in flight.
- `implemented` — code matches SSOT.
- `drift` — code diverges from SSOT.
- `deprecated` — slated for removal.

### Mutating SSOT

How SSOT is mutated after seeding is **not defined by kg-workflow** — pick a process that fits this repo (e.g. a Decision Log + replay script, hand-edits with code review, or a separate workflow tool). Whatever you pick, never edit `.understand-anything-ssot/knowledge-graph.json` in a way that contradicts the chosen process.

{{SSOT_DOCS_LINE}}

See `.understand-anything-ssot/README.md` for the SSOT field reference.
<!-- kg-workflow:end -->
