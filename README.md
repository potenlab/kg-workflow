# kg-workflow

> **A side-effect radar for your codebase.**
> Every time you ask Claude to build or change a feature, kg-workflow runs a pre-flight check *first* — and warns you what else that change will touch *before* a single line is edited.

Built on [understand-anything](https://github.com/Lum1104/Understand-Anything) and [Entire](https://docs.entire.io).

---

## The problem it solves

You ask for a "small change." Claude edits the file. Three other features quietly break, because nobody flagged that 8 things depended on that function — or that this code was already deprecated, or that you decided *not* to do this exact thing two weeks ago.

**kg-workflow stops that.** Before any substantive change, it answers three questions in parallel:

| Question | Agent | Source |
|----------|-------|--------|
| What is this code **supposed** to do? (intent, contract, how much you're allowed to touch) | `kg-ssot-check` | SSOT KG |
| What **depends** on it? (the blast radius — the actual side-effect signal) | `kg-impl-check` | Impl KG |
| Did we **already decide** something about this? | `kg-history-check` | Entire history |

A dispatcher fans those three out, merges the answers, and hands Claude a short briefing. **If the change is risky, you get a warning naming the exact files, nodes, and decisions at stake — not a vague "this might affect things."**

---

## Quick start

```bash
cd your-repo
/kg-init      # one-time bootstrap
/clear        # so the agents register in the session
```

Then just work normally. Ask for a feature. The pre-flight runs automatically.

---

## What you get from `/kg-init`

| Artifact | What it is |
|----------|-----------|
| **Impl KG** — `.understand-anything/knowledge-graph.json` | What the code **IS**. Built by `understand-anything` and **auto-updated on every git commit** (kg-init enables `--auto-update`), so the blast-radius data never goes stale. |
| **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` | What the code **SHOULD BE**. Seeded once from the Impl KG with intent fields: `status`, `acceptance`, `contract`, `rationale_ref`, `touch_budget`. |
| **Entire tracking** — `.entire/` | Local prompt/decision history. Auto-enabled if the `entire` CLI is present. |
| **The agent fleet** | `kg-context-dispatch` (orchestrator) + the three checkers above. |
| **Auto-fire hooks** | A `UserPromptSubmit` hook nudges Claude to run the dispatch on every real prompt — and self-skips greetings and trivial follow-ups. |
| **Seed script** | `scripts/ssot_seed.py` for deterministic re-seeding. |

---

## How the pre-flight runs

```
User prompt: "add a retry to the upload handler"
   │
   ▼
Hook fires → main Claude calls kg-context-dispatch
   │
   ▼
kg-context-dispatch   (classify the prompt → extract topic hints)
   │
   ▼  fan out IN PARALLEL — one message, three agents
   ├───────────────────────┬───────────────────────┐
   ▼                       ▼                       ▼
kg-ssot-check        kg-impl-check          kg-history-check
"what SHOULD          "what depends           "did we decide
 it do?"               on it?"                 this already?"
status, acceptance,   matching nodes +        prior prompts,
contract,             DEPENDENTS  ◄── the     decisions,
touch_budget          side-effect signal      sessions
   │                       │                       │
   └───────────────────────┴───────────────────────┘
                           │
                           ▼
kg-context-dispatch   (merge + compute side_effect_warning)
                           │
                           ▼
Main Claude gets a compact JSON briefing as authoritative context.
If side_effect_warning = true → it shows you the warning BEFORE editing.
```

Because the three checkers run in one parallel message, wall-clock time is `max(3)`, not `sum(3)`.

---

## When you get a warning

`kg-context-dispatch` raises `side_effect_warning: true` when:

1. The work would breach a node's **`touch_budget`** (SSOT says "don't change more than X here").
2. An affected node has **> 3 dependents** and the change is behavioral — i.e. real blast radius (Impl).
3. An in-scope SSOT node is **`deprecated`** or in **`drift`**.
4. A **prior Entire decision contradicts** what the prompt proposes.

Every warning cites specific node IDs, file paths, and decision IDs. The point is to make the side effect *concrete and actionable*, so you can decide before the edit — not debug after.

---

## Why it's cheap

Sub-agents have isolated context windows. Your main session only pays for:

- one dispatcher prompt (~500 tokens), and
- one compact JSON briefing back (~1.5–3k tokens, capped).

The three checkers read full KG fragments and run `entire search` **in their own context** — that work never bills against your main session. And the dispatcher's classifier skips trivial prompts entirely, so you don't pay the multi-agent cost on every "ok" or "show me the README."

---

## Prerequisites

- **`understand-anything` plugin** — kg-workflow calls its `/understand` skill to build the Impl KG.
- **`python3` 3.11+** — for the seed script.
- **A git repo** — `kg-init` refuses to run outside one.
- **An SSOT process docs directory** (e.g. `docs/ssot/`). If missing, `kg-init` stops and prompts you (see below).
- **Optional but recommended: the `entire` CLI** ([docs.entire.io](https://docs.entire.io)). Without it, `kg-history-check` degrades gracefully — it returns `entire_not_initialized` instead of failing.

---

## Install

### Claude Code (recommended)

```
/plugin marketplace add potenlab/kg-workflow
/plugin install kg-workflow
```

After install, run `/clear` so the agents register in the session.

### Other agents (Codex, Gemini CLI, OpenCode, etc.)

```
curl -fsSL https://raw.githubusercontent.com/potenlab/kg-workflow/main/install.sh | bash -s <platform>
```

Supported platforms: `codex`, `gemini`, `opencode`, `vscode`, `vibe`. See `install.sh --help`.

---

## What `/kg-init` does, step by step

1. **Detect SSOT process docs.** If none of `docs/ssot/`, `docs/SSOT/`, `ssot/`, `.ssot/`, or `docs/decisions/` exists, it stops and prompts:
   - `/kg-init --ssot-docs <path>` — I have docs at a custom path
   - set up docs first with your own tool, then re-run
   - `/kg-init --ssot-docs none` — proceed with no docs reference
2. Build the Impl KG via `/understand --full --auto-update` — the `--auto-update` arms understand-anything's commit hook so the Impl KG refreshes incrementally on every `git commit` / `merge` / `rebase`. (The SSOT KG stays manual — intent is mutated deliberately, not regenerated.)
3. Drop `scripts/ssot_seed.py`.
4. Seed the SSOT KG from the Impl KG.
5. Drop `.understand-anything-ssot/{README,schema}.md`.
6. Write a root `.understandignore`.
7. Append the kg-workflow stanza to `CLAUDE.md` (dispatch rule + status semantics + warning rule).
8. **Initialize Entire** via `entire enable` if the CLI is installed; otherwise warn and continue.
9. Verify the agents register.

Then `/clear` and try a real prompt — Claude should dispatch the pre-flight before answering.

---

## Scope

kg-workflow bootstraps and wires the side-effect pre-flight. It deliberately does **not**:

- Define a Decision Log, replay tool, or drift detector.
- Scaffold `docs/ssot/` or any process directory (it prompts you instead).
- Take a position on how you mutate SSOT after the initial seed.

---

## Repo layout

```
kg-workflow/
├── .claude-plugin/
│   └── marketplace.json
├── kg-workflow-plugin/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   └── kg-init/SKILL.md             # the /kg-init orchestration
│   ├── agents/                          # the side-effect pre-flight fleet
│   │   ├── kg-context-dispatch.md       # orchestrator — main Claude calls this
│   │   ├── kg-ssot-check.md             # intent: status, acceptance, touch_budget
│   │   ├── kg-impl-check.md             # blast radius: nodes + dependents
│   │   └── kg-history-check.md          # prior decisions via Entire
│   ├── hooks/hooks.json                 # auto-fire the dispatch on each prompt
│   └── templates/
│       ├── claude-md-snippet.md         # appended to user's CLAUDE.md
│       ├── understandignore             # root .understandignore
│       ├── ssot/{README,schema}.md
│       └── scripts/ssot_seed.py
├── install.sh
├── README.md
└── LICENSE
```

## License

MIT.
