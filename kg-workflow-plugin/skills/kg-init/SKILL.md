---
name: kg-init
description: Bootstrap a dual knowledge-graph layout in the current repo — Impl KG (what code IS, via understand-anything) + SSOT KG (what code SHOULD BE, seeded with SSOT defaults) — and wire the root CLAUDE.md to consult SSOT first, Impl second.
argument-hint: ["[--path <dir>] [--scripts-dir <dir>] [--no-claude-md] [--language <lang>]"]
---

# /kg-init

One-shot bootstrap for the dual-KG pattern. Run this **once** per repo, on a clean tree.

It will:

1. Build the **Impl KG** by invoking the `understand` skill (`understand-anything` plugin).
2. Seed the **SSOT KG** by projecting the Impl KG into `.understand-anything-ssot/` with SSOT fields added.
3. Install `scripts/ssot_seed.py` so the seed can be replayed deterministically.
4. Append a **kg-workflow** stanza to the root `CLAUDE.md` telling Claude to **consult SSOT first, Impl second** on every code question.

It will **not**:

- Scaffold a Decision Log, meeting transcripts, or any `docs/ssot/` content. How SSOT is mutated after seeding is out of scope for this plugin — that's a separate concern (a process / another tool / your own conventions).
- Ship drift-detection or replay scripts beyond the seed. Pick or build those separately.

## Options

`$ARGUMENTS` may contain:

- `--path <dir>` — target repo root (default: current working directory).
- `--scripts-dir <dir>` — where to install `ssot_seed.py` (default: `scripts/`).
- `--no-claude-md` — skip the CLAUDE.md edit (advanced; you must wire SSOT-first manually).
- `--language <lang>` — passed through to `/understand` for natural-language output (default: `en`).

## Hard preconditions (abort if violated)

Before doing anything destructive, verify all of the following. If any fail, **STOP** with a clear message — do not partially init.

1. `PROJECT_ROOT` is a directory and a git repo (`git -C "$PROJECT_ROOT" rev-parse --git-dir` succeeds).
2. The `understand-anything` plugin's `understand` skill is reachable in this Claude Code session. If it is not, tell the user to `/plugin install understand-anything` from the official marketplace, then re-run `/kg-init`.
3. `python3 --version` reports 3.11+.
4. None of these paths exist yet (refuse otherwise):
   - `$PROJECT_ROOT/.understand-anything/`
   - `$PROJECT_ROOT/.understand-anything-ssot/`
   - `$PROJECT_ROOT/$SCRIPTS_DIR/ssot_seed.py`

   If any exist, report which ones and abort. The user can delete or rename them.

## Resolve the plugin root

Locate this plugin's installed path so we can copy templates and the seed script out of it.

```bash
# Try, in order: $CLAUDE_PLUGIN_ROOT, common install symlinks, then realpath of the SKILL location.
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$PLUGIN_ROOT" ]; then
  for candidate in \
    "$HOME/.claude/plugins/cache/kg-workflow/kg-workflow"/*/kg-workflow-plugin \
    "$HOME/.kg-workflow/repo/kg-workflow-plugin" \
    "$HOME/.claude/skills/kg-init/../.."; do
    [ -d "$candidate/templates" ] && PLUGIN_ROOT="$(cd "$candidate" && pwd -P)" && break
  done
fi
if [ -z "$PLUGIN_ROOT" ] || [ ! -d "$PLUGIN_ROOT/templates" ]; then
  echo "ERROR: cannot locate kg-workflow plugin root (templates/ not found)." >&2
  echo "If this is a custom install, set CLAUDE_PLUGIN_ROOT to the kg-workflow-plugin directory." >&2
  exit 1
fi
```

## Phase 1 — Build the Impl KG

Invoke the `understand` skill against `$PROJECT_ROOT` with `--full`. Forward `--language <lang>` if the user passed it.

The `understand` skill writes `$PROJECT_ROOT/.understand-anything/knowledge-graph.json` and friends. Do **not** continue until it reports success.

If `/understand` does not produce `.understand-anything/knowledge-graph.json`, abort and surface the failure — do not attempt to seed SSOT from a missing file.

## Phase 2 — Install the seed script

```bash
mkdir -p "$PROJECT_ROOT/$SCRIPTS_DIR"
cp "$PLUGIN_ROOT/templates/scripts/ssot_seed.py" "$PROJECT_ROOT/$SCRIPTS_DIR/ssot_seed.py"
chmod +x "$PROJECT_ROOT/$SCRIPTS_DIR/ssot_seed.py"
```

## Phase 3 — Seed the SSOT KG

```bash
python3 "$PROJECT_ROOT/$SCRIPTS_DIR/ssot_seed.py" \
  --impl "$PROJECT_ROOT/.understand-anything/knowledge-graph.json" \
  --out  "$PROJECT_ROOT/.understand-anything-ssot/knowledge-graph.json"
```

`ssot_seed.py` is responsible for:

- Reading the Impl KG verbatim.
- Adding SSOT defaults to every node (`status: "inherited", acceptance: null, contract: null, rationale_ref: [], touch_budget: null`), edge (`status: "inherited", rationale_ref: []`), and layer (`status: "inherited", acceptance: null, rationale_ref: []`).
- Writing `.understand-anything-ssot/{knowledge-graph.json, config.json, meta.json}`.
  - `config.json`: `{"autoUpdate": false}`
  - `meta.json`: `{ssot_version, seeded_from_ua_commit, seeded_at, node_count, edge_count, layer_count, confirmed_nodes: 0, confirmed_layers: 0}`

## Phase 4 — Install SSOT documentation

```bash
mkdir -p "$PROJECT_ROOT/.understand-anything-ssot"
cp "$PLUGIN_ROOT/templates/ssot/README.md" "$PROJECT_ROOT/.understand-anything-ssot/README.md"
cp "$PLUGIN_ROOT/templates/ssot/schema.md" "$PROJECT_ROOT/.understand-anything-ssot/schema.md"
```

## Phase 5 — Write the root `.understandignore`

If `$PROJECT_ROOT/.understand-anything/.understandignore` does not already cover a sensible default scope, overwrite it with the kg-workflow template:

```bash
cp "$PLUGIN_ROOT/templates/understandignore" "$PROJECT_ROOT/.understand-anything/.understandignore"
```

(The template excludes `node_modules/`, `.next/`, `.venv/`, tests, docs, KG self-state, and common build caches — sane defaults for mixed-language repos.)

## Phase 6 — Wire CLAUDE.md (skip if `--no-claude-md`)

Append the kg-workflow stanza to the root `CLAUDE.md`. If `CLAUDE.md` does not exist, create it with this stanza as the entire body.

```bash
SNIPPET="$PLUGIN_ROOT/templates/claude-md-snippet.md"
TARGET="$PROJECT_ROOT/CLAUDE.md"
MARKER="<!-- kg-workflow:begin -->"

if [ -f "$TARGET" ] && grep -qF "$MARKER" "$TARGET"; then
  echo "[kg-init] CLAUDE.md already contains a kg-workflow stanza — skipping append."
else
  {
    [ -f "$TARGET" ] && echo ""
    cat "$SNIPPET"
  } >> "$TARGET"
fi
```

The snippet tells Claude:

- **Consult `.understand-anything-ssot/knowledge-graph.json` FIRST** for every code question — it represents intent (`status`, `acceptance`, `contract`, `touch_budget`, `rationale_ref`).
- **Then consult `.understand-anything/knowledge-graph.json`** for what the code actually is.
- If SSOT and Impl disagree on a node, surface the drift and prefer SSOT unless the user explicitly says otherwise.
- Respect `touch_budget`; derive tests from `acceptance`.

The snippet is delimited by `<!-- kg-workflow:begin -->` and `<!-- kg-workflow:end -->` so future updates can find and replace it cleanly.

## Phase 7 — Report

Print a summary:

```
[kg-init] ✓ Impl KG    .understand-anything/        (N nodes, M edges, L layers)
[kg-init] ✓ SSOT KG    .understand-anything-ssot/   (seeded from Impl)
[kg-init] ✓ Script     scripts/ssot_seed.py
[kg-init] ✓ CLAUDE.md  appended kg-workflow stanza

Next steps:
  1. Read .understand-anything-ssot/README.md to understand the SSOT fields.
  2. Decide how you want to mutate SSOT going forward (out of scope for this plugin) —
     options include a Decision Log + replay tool, direct hand-edits with code review,
     or a separate workflow tool.
```

## Error handling

- If any phase fails, **STOP** — do not continue to later phases. Tell the user exactly what went wrong and which files were partially written.
- Never delete files the user wrote. Only the templates this skill installed are safe to remove on rollback.
- If `/understand` succeeds but SSOT seed fails, leave the Impl KG in place — the user can re-run only the SSOT phases manually.
