# kg-workflow

Dual knowledge-graph workflow for any codebase, installed as a Claude Code plugin. Built on top of [understand-anything](https://github.com/Lum1104/Understand-Anything).

Run `/kg-init` once. You get:

- **Impl KG** — `.understand-anything/knowledge-graph.json` — what the code IS. Maintained by `understand-anything`.
- **SSOT KG** — `.understand-anything-ssot/knowledge-graph.json` — what the code SHOULD BE. Projected from a Decision Log at `docs/ssot/decisions/`.
- **Scripts** — `scripts/ssot_{seed,replay,diff}.py` for bootstrapping, replaying decisions, and detecting drift.
- **CLAUDE.md stanza** — wires Claude to always consult SSOT first, Impl second.

## Why

Knowledge graphs of code answer "what is" — good for navigation, weak for guiding new work. An SSOT KG answers "what should be" — drift between the two is the signal you actually want to see before a PR.

The Decision Log is the real source of truth. The SSOT KG is just a projection of it. Replay is idempotent — two runs produce the same KG byte-for-byte.

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

## Usage

```
cd your-repo
/kg-init
```

That's it. `kg-init` will:

1. Build the Impl KG via `/understand --full` against the repo root.
2. Seed the SSOT KG from the Impl KG (every node, edge, layer gets SSOT defaults).
3. Scaffold `docs/ssot/decisions/` (Decision Log) and `docs/ssot/meetings/` (audio + transcripts).
4. Drop `scripts/ssot_seed.py`, `scripts/ssot_replay.py`, `scripts/ssot_diff.py`.
5. Append a kg-workflow stanza to `CLAUDE.md` so Claude consults SSOT first, Impl second.

### Day-2 workflow

```bash
# After a planning meeting:
mlx_whisper --output-dir docs/ssot/meetings/transcripts/ \
            --output-format txt docs/ssot/meetings/raw/2026-06-01-foundations.m4a

# Append DL entries to docs/ssot/decisions/index.jsonl (see template README for grammar)
# Then:
python3 scripts/ssot_replay.py
python3 scripts/ssot_diff.py        # before every non-trivial PR
```

## What `/kg-init` will NOT do

- Overwrite an existing `.understand-anything/` or `.understand-anything-ssot/` — it refuses and asks you to delete first.
- Edit code outside `CLAUDE.md`, `.understand-anything*/`, `docs/ssot/`, and `scripts/`.
- Hide failures. If `/understand` fails, `kg-init` stops there and surfaces the error.

## Repo layout

```
kg-workflow/
├── .claude-plugin/
│   ├── marketplace.json
│   └── plugin.json
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
│       ├── decisions/
│       │   └── README.md               # Decision Log format + effect grammar
│       └── scripts/
│           ├── ssot_seed.py
│           ├── ssot_replay.py
│           └── ssot_diff.py
├── install.sh                          # one-line installer for non-Claude-Code platforms
├── README.md
└── LICENSE
```

## License

MIT.
