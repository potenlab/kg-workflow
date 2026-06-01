# Decision Log

The **real SSOT**. Append-only. The SSOT KG (`.understand-anything-ssot/knowledge-graph.json`) is a projection of this log.

## Layout

```
docs/ssot/
├── decisions/
│   ├── README.md             # this file
│   ├── index.jsonl           # append-only log (one JSON line per entry)
│   └── entries/              # optional long-form .md per entry
└── meetings/
    ├── raw/                  # original audio recordings
    └── transcripts/          # mlx_whisper output, one .txt per raw
```

## Entry format

Each entry is one JSON line in `index.jsonl`. Optional long-form markdown lives at `entries/<id>.md`.

```json
{
  "id": "DL-2026-06-01-001",
  "meeting_id": "2026-06-01-foundations",
  "claim": "All publish operations must go through PublishGateway; direct adapter calls are forbidden.",
  "rationale": "Side-effects centralized in one place; lets us add per-channel rate-limiting later without touching call sites.",
  "supersedes": null,
  "scope": ["engine.publish", "engine.adapters.*"],
  "effects": [
    {
      "op": "set",
      "target": {"kind": "node", "id": "engine.publish.PublishGateway"},
      "fields": {
        "status": "spec",
        "acceptance": "Every publish path enters via PublishGateway.publish(); no adapter is called from outside it.",
        "contract": "publish(ChannelId, ArticleId) -> PublishResult; raises RateLimited, AdapterError.",
        "touch_budget": ["engine/src/publish/**", "engine/src/adapters/**"]
      }
    }
  ],
  "long_form": "entries/DL-2026-06-01-001.md"
}
```

## Fields

| field | required | meaning |
|---|---|---|
| `id` | yes | `DL-YYYY-MM-DD-NNN`, monotonic within the day. Never reuse. |
| `meeting_id` | yes | Transcript filename slug, or `null` for ad-hoc decisions. |
| `claim` | yes | One-sentence statement of the decision. |
| `rationale` | yes | One-paragraph WHY. |
| `supersedes` | no | DL ID this entry replaces (creates a chain — never edit old entries). |
| `scope` | yes | List of layer or node IDs affected (informational; effects are authoritative). |
| `effects` | yes | List of mutations to apply to the SSOT KG. See effect grammar. |
| `long_form` | no | Relative path to a markdown file with extended context. |

## Effect grammar

Each effect mutates the SSOT KG. Replay applies effects in jsonl order; replay must be idempotent.

### `set`

Merge `fields` into a target's SSOT block. Target is a node, edge, or layer by ID.

```json
{"op": "set", "target": {"kind": "node", "id": "<node_id>"}, "fields": {"status": "spec", "acceptance": "...", "touch_budget": ["..."]}}
{"op": "set", "target": {"kind": "edge", "id": "<edge_id>"}, "fields": {"status": "confirmed"}}
{"op": "set", "target": {"kind": "layer", "id": "<layer_id>"}, "fields": {"status": "confirmed", "acceptance": "..."}}
```

### `add_node`

Append a node to `nodes[]`. Used when SSOT defines a component that doesn't exist in Impl yet (`missing_in_impl`).

```json
{"op": "add_node", "node": {"id": "...", "type": "...", "name": "...", "filePath": "...", "status": "spec", "acceptance": "...", "contract": "...", "rationale_ref": ["DL-..."], "touch_budget": ["..."]}}
```

### `add_edge`

Append an edge to `edges[]`.

```json
{"op": "add_edge", "edge": {"source": "...", "target": "...", "type": "depends_on", "status": "spec", "rationale_ref": ["DL-..."]}}
```

### `deprecate`

Set `status: "deprecated"` on a target.

```json
{"op": "deprecate", "target": {"kind": "node", "id": "..."}}
```

### `remove`

Drop a target. Use sparingly — prefer `deprecate` so history is preserved.

```json
{"op": "remove", "target": {"kind": "node", "id": "..."}}
```

## Conventions

1. **One claim per entry.** Split if needed.
2. **Never edit existing entries.** To change a decision, write a new entry with `supersedes: "<old-id>"`.
3. **Never edit the SSOT KG directly.** Only `ssot_replay.py` may write to it.
4. **Replay is idempotent.** Running it twice produces a byte-identical KG.
5. **IDs are monotonic within the day.** `DL-2026-06-01-001`, `-002`, `-003`. Across days the counter resets.
6. **`meeting_id` references the transcript filename.** Drop the `.txt` extension and the directory prefix. Use `null` for entries with no meeting (e.g. async decisions in a doc).

## Pipeline

```
1. Drop audio in docs/ssot/meetings/raw/YYYY-MM-DD-slug.{m4a,mp3,wav}
2. Transcribe:
     mlx_whisper --condition-on-previous-text False \
                 --hallucination-silence-threshold 1 \
                 --output-dir docs/ssot/meetings/transcripts/ \
                 --output-format txt raw/<file>
3. Read transcript, extract decisions, append DL entries to index.jsonl
   (+ optional long-form .md per entry).
4. python3 scripts/ssot_replay.py        # rebuild SSOT KG
5. python3 scripts/ssot_diff.py          # drift report
6. Commit meetings/ + decisions/ + SSOT KG together.
```
