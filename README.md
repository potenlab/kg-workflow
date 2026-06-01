# kg-workflow

Bootstraps a dual knowledge-graph layout in any repo, installed as a Claude Code plugin. Built on top of [understand-anything](https://github.com/Lum1104/Understand-Anything).

Run `/kg-init` once. You get:

- **Impl KG** — `.understand-anything/knowledge-graph.json` — what the code IS. Maintained by `understand-anything`.
- **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` — what the code SHOULD BE. Seeded once from the Impl KG with SSOT defaults (`status`, `acceptance`, `contract`, `rationale_ref`, `touch_budget`).
- **Seed script** — `scripts/ssot_seed.py` for deterministic re-seeding if you ever need it.
- **CLAUDE.md stanza** — wires Claude to always consult SSOT first, Impl second.

## Scope

kg-workflow is **deliberately narrow**. It only bootstraps the two KGs and tells Claude how to read them.

It does **not**:

- Define a Decision Log, replay tool, or drift detector.
- Scaffold `docs/ssot/` or any process directory.
- Take a position on how you mutate SSOT after seeding.

How SSOT evolves is your call — pick a Decision Log + replay tool, hand-edit with code review, or bring a separate workflow. kg-workflow stops at the seed.

## Install

### Claude Code (recommended)

```
/plugin marketplace add potenlab/kg-workflow
/plugin install kg-workflow
```

### Other agents (Codex, Gemini CLI, OpenCode, etc.)

```
curl -fsSL https://raw.githubusercontent.com/potenlab/kg-workflow/main/install.sh | bash -s <platform>
```

Supported platforms: `codex`, `gemini`, `opencode`, `vscode`, `vibe`. See `install.sh --help`.

## Prerequisites

- `understand-anything` plugin installed (kg-workflow calls its `/understand` skill to build the Impl KG).
- `python3` 3.11+ on the user's machine.
- A git repo. `kg-init` refuses to run outside one.
- **An SSOT process docs directory** (e.g. `docs/ssot/`, `docs/decisions/`, `ssot/`, `.ssot/`). kg-workflow does NOT create this — it only references it from CLAUDE.md. If `/kg-init` can't find one, it stops and prompts you (see below).

## Usage

```
cd your-repo
/kg-init
```

`kg-init` will:

1. **Detect your SSOT process docs.** If none of `docs/ssot/`, `docs/SSOT/`, `ssot/`, `.ssot/`, or `docs/decisions/` is present, kg-init **stops and prompts** you with three options:
   - `/kg-init --ssot-docs <path>` — I have docs at a custom path
   - Initialize docs first using your own tool/process, then re-run
   - `/kg-init --ssot-docs none` — proceed with no docs reference
2. Build the Impl KG via `/understand --full` against the repo root.
3. Drop `scripts/ssot_seed.py`.
4. Seed the SSOT KG from the Impl KG (every node, edge, layer gets SSOT defaults).
5. Drop `.understand-anything-ssot/{README,schema}.md`.
6. Write a root `.understandignore` if one isn't already present.
7. Append a kg-workflow stanza to `CLAUDE.md` so Claude consults SSOT first, Impl second — and, when configured, points at your SSOT process docs.

### Why the docs prompt is hard, not auto

kg-workflow won't silently default to "no docs" on your behalf. Forcing the explicit re-invocation makes the choice visible in your terminal history and nudges you to actually set up a mutation process (Decision Log, replay tool, whatever) before locking in the KG layout.

## What `/kg-init` will NOT do

- Overwrite an existing `.understand-anything/` or `.understand-anything-ssot/` — it refuses and asks you to delete first.
- Edit code outside `CLAUDE.md`, `.understand-anything*/`, and `scripts/ssot_seed.py`.
- Hide failures. If `/understand` fails, `kg-init` stops there and surfaces the error.

## Repo layout

```
kg-workflow/
├── .claude-plugin/
│   └── marketplace.json
├── kg-workflow-plugin/
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   │   └── kg-init/SKILL.md            # the /kg-init orchestration
│   └── templates/
│       ├── claude-md-snippet.md        # appended to user's CLAUDE.md
│       ├── understandignore            # root .understandignore
│       ├── ssot/
│       │   ├── README.md
│       │   └── schema.md
│       └── scripts/
│           └── ssot_seed.py            # only script shipped
├── install.sh                          # one-line installer for non-Claude-Code platforms
├── README.md
└── LICENSE
```

## License

MIT.
