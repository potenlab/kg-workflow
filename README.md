# kg-workflow

A Claude Code plugin that bootstraps a **dual knowledge-graph + parallel-context-dispatch** workflow in any repo. Built on top of [understand-anything](https://github.com/Lum1104/Understand-Anything) and [Entire](https://docs.entire.io).

Run `/kg-init` once. You get:

- **Impl KG** — `.understand-anything/knowledge-graph.json` — what the code IS. Maintained by `understand-anything`.
- **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` — what the code SHOULD BE. Seeded once from the Impl KG with SSOT defaults (`status`, `acceptance`, `contract`, `rationale_ref`, `touch_budget`).
- **Entire session tracking** — `.entire/` — local prompt/decision history, automatically enabled if the `entire` CLI is present.
- **Four sub-agents** — `kg-context-dispatch`, `kg-ssot-check`, `kg-impl-check`, `kg-history-check` — wired into CLAUDE.md so every substantive prompt gets a pre-flight context briefing and a side-effect warning.
- **Seed script** — `scripts/ssot_seed.py` for deterministic re-seeding if you ever need it.

## How it works at runtime

Every substantive prompt (not greetings or "looks good") triggers this flow:

```
User prompt
   │
   ▼
Main Claude reads CLAUDE.md → Task(kg-context-dispatch)
   │
   ▼
kg-context-dispatch  (Phase A: cheap classify; Phase B: extract topic hints)
   │
   ▼  Phase C: fan out IN PARALLEL — single message, three Task calls
   ├──────────────────────────┬──────────────────────────┐
   ▼                          ▼                          ▼
kg-ssot-check            kg-impl-check             kg-history-check
.understand-anything-    .understand-anything/    .entire/ via
ssot/ → status,          → relevant nodes +       entire search →
acceptance, contract,    DEPENDENTS (the          prior decisions,
touch_budget,            side-effect signal)      sessions, prompts
rationale_ref
   │                          │                          │
   └──────────────────────────┴──────────────────────────┘
                              │
                              ▼
kg-context-dispatch  (Phase D: synthesize + compute side_effect_warning)
                              │
                              ▼
Main Claude proceeds with compact JSON briefing as authoritative context.
If side_effect_warning=true, surface warning_text to user BEFORE editing.
```

### Side-effect warning rule

`kg-context-dispatch` flags `side_effect_warning: true` when:

1. Proposed work would breach a node's `touch_budget` (from SSOT).
2. An affected node has > 3 dependents (from Impl) and the change is behavioral.
3. An in-scope SSOT node is `deprecated` or `drift`.
4. A prior Entire decision contradicts what the prompt proposes.

The warning cites specific node IDs / file paths / DL IDs — not hand-wavy "this might affect things".

### Token model

Sub-agents have isolated context windows. Main Claude pays for:

- One dispatcher prompt (~500 tokens)
- One compact JSON briefing back (~1500–3000 tokens, capped)

The three leaf agents (read full KG fragments, run `entire search`, etc.) **don't bill against the main session's context**. And because they run in one parallel message, wall-clock = `max(3)` not `sum(3)`.

The dispatcher's Phase A classifier skips trivial prompts entirely — you don't pay the 4-agent cost on every "ok" or "show me the README".

## Scope

kg-workflow bootstraps and wires the dispatch flow. It does **not**:

- Define a Decision Log, replay tool, or drift detector.
- Scaffold `docs/ssot/` or any process directory (kg-init prompts the user if no such dir is detected).
- Take a position on how you mutate SSOT after seeding.

## Install

### Claude Code (recommended)

```
/plugin marketplace add potenlab/kg-workflow
/plugin install kg-workflow
```

After install, run `/clear` so the four agents register in the session.

### Other agents (Codex, Gemini CLI, OpenCode, etc.)

```
curl -fsSL https://raw.githubusercontent.com/potenlab/kg-workflow/main/install.sh | bash -s <platform>
```

Supported platforms: `codex`, `gemini`, `opencode`, `vscode`, `vibe`. See `install.sh --help`.

## Prerequisites

- `understand-anything` plugin installed (kg-workflow calls its `/understand` skill to build the Impl KG, and its agents are useful for KG lookup).
- `python3` 3.11+ on the user's machine.
- A git repo. `kg-init` refuses to run outside one.
- An SSOT process docs directory (e.g. `docs/ssot/`). If missing, kg-init stops and prompts — see below.
- **Optional but recommended:** the `entire` CLI from https://docs.entire.io. Without it, `kg-history-check` returns `entire_not_initialized` on every dispatch (graceful degrade, not fatal).

## Usage

```
cd your-repo
/kg-init
```

`kg-init` will, in order:

1. **Detect SSOT process docs.** If none of `docs/ssot/`, `docs/SSOT/`, `ssot/`, `.ssot/`, or `docs/decisions/` is present, stop and prompt:
   - `/kg-init --ssot-docs <path>` — I have docs at a custom path
   - Set up docs first using your own tool/process, then re-run
   - `/kg-init --ssot-docs none` — proceed with no docs reference
2. Build the Impl KG via `/understand --full`.
3. Drop `scripts/ssot_seed.py`.
4. Seed the SSOT KG from the Impl KG.
5. Drop `.understand-anything-ssot/{README,schema}.md`.
6. Write a root `.understandignore`.
7. Append the kg-workflow stanza to `CLAUDE.md` (dispatch rule + status semantics + warning rule).
8. **Initialize Entire** via `entire enable` if the CLI is installed. Otherwise warn and continue.
9. Verify the four agents register.

Then run `/clear` and try a substantive prompt — main Claude should now dispatch via `kg-context-dispatch` before answering.

### Why the dispatch is a CLAUDE.md guideline, not a hard hook

Claude Code skills don't have a "pre-prompt hook" mechanism. The CLAUDE.md stanza is a strong guideline Claude follows reliably for substantive prompts, but it's not enforced at the harness level. If you want hard enforcement, add a `UserPromptSubmit` hook to your project's `.claude/settings.json` — out of scope for this plugin, but a sensible follow-up.

## Repo layout

```
kg-workflow/
├── .claude-plugin/
│   └── marketplace.json
├── kg-workflow-plugin/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   └── kg-init/SKILL.md             # the /kg-init orchestration
│   ├── agents/                          # parallel-dispatch fleet
│   │   ├── kg-context-dispatch.md       # entry point — main Claude calls this
│   │   ├── kg-ssot-check.md             # SSOT lookup (status, acceptance, touch_budget)
│   │   ├── kg-impl-check.md             # Impl lookup + dependents (side-effect signal)
│   │   └── kg-history-check.md          # Entire prior-prompt search
│   └── templates/
│       ├── claude-md-snippet.md         # appended to user's CLAUDE.md
│       ├── understandignore             # root .understandignore
│       ├── ssot/{README,schema}.md
│       └── scripts/ssot_seed.py         # only script shipped
├── install.sh
├── README.md
└── LICENSE
```

## License

MIT.
