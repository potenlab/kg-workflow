<!-- kg-workflow:begin -->
## Knowledge graphs (SSOT-first, Impl-second, dispatched)

This repo is bootstrapped with [kg-workflow](https://github.com/potenlab/kg-workflow). Three artifacts:

- **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` — what the code **should be**. Each node carries `status`, `acceptance`, `contract`, `rationale_ref`, and `touch_budget` on top of the UA schema. `autoUpdate: false`.
- **Impl KG** — `.understand-anything/knowledge-graph.json` — what the code **actually is**. Built and refreshed by the `understand-anything` plugin from source. `autoUpdate: true`.
- **Entire** — `.entire/` — local session/prompt history, queried via the `entire` CLI.

### The dispatch rule (the one rule that matters)

**Before any substantive code or architecture work, dispatch to the `kg-context-dispatch` subagent.** That agent fans out in parallel to three checkers and returns a compact briefing. It is the entry point — do not query the KGs or Entire directly from the main session for routine work.

Invoke via the Task tool:

```
Task(
  subagent_type="kg-context-dispatch",
  prompt={ "prompt": "<the user's verbatim prompt>", "intent_hint": "<your one-line read>" }
)
```

`kg-context-dispatch` will:

1. **Classify cheaply.** If the prompt is trivial (greeting, file-listing, meta question, conversational follow-up, or about the workflow tooling itself), it returns `{status: "skipped"}` fast. Don't waste a dispatch on every "looks good".
2. **Fan out in parallel** (single message, three Task calls) to:
   - `kg-ssot-check` — what SSOT says about the affected nodes (status, acceptance, contract, touch_budget, rationale_ref).
   - `kg-impl-check` — what Impl says, including the **dependents** of the affected nodes — the side-effect signal.
   - `kg-history-check` — prior prompts / decisions / sessions in this area, via `entire search`.
3. **Synthesize + warn.** Returns a compact JSON briefing plus a `side_effect_warning` flag with `warning_text` whenever:
   - The proposed work would breach a node's `touch_budget`.
   - An affected node has > 3 dependents and the change is behavioral.
   - An in-scope SSOT node is `deprecated` or `drift`.
   - A prior decision in `kg-history-check` contradicts what the prompt proposes.

### How to act on the briefing

- **`status: "skipped"`** → proceed normally; the prompt was trivial.
- **`side_effect_warning: true`** → surface `warning_text` to the user BEFORE writing any code. Ask them to confirm or scope down. Do not silently expand `touch_budget`.
- **No warning** → use `recommended_next_step` as your first action, and treat `ssot.relevant_nodes` as authoritative for intent and `impl.relevant_nodes` as authoritative for current state.

### When SSOT and Impl disagree

The briefing surfaces this as drift. Default to **SSOT intent** unless the user explicitly overrides. Never silently align Impl to old assumptions.

### Status semantics (from SSOT)

`inherited | confirmed | spec | wip | implemented | drift | deprecated`

A `spec` node means: intent declared, code not there yet — when you implement it, expect it to flip to `implemented` after the next drift check.

### Mutating SSOT

How SSOT is mutated after seeding is **not defined by kg-workflow**. Pick a process (Decision Log + replay, hand-edits with code review, or a separate workflow tool). Never edit `.understand-anything-ssot/knowledge-graph.json` in a way that contradicts the chosen process.

{{SSOT_DOCS_LINE}}

See `.understand-anything-ssot/README.md` for the SSOT field reference.
<!-- kg-workflow:end -->
