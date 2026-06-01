# SSOT KG Schema

Inherits the UA Impl KG schema (`.understand-anything/knowledge-graph.json`) verbatim. Adds SSOT-specific fields per node, edge, and layer, plus top-level metadata.

## Top-level

Same as UA: `version, project, nodes, edges, layers, tour`.

Additional:

- `ssot_version: "1.0.0"`
- `seeded_from_ua_commit: "<sha>"` — Impl KG git commit used at seed time.
- `seeded_at: "<iso8601>"` — seed timestamp.

## Per-node SSOT fields

| field | type | meaning |
|---|---|---|
| `status` | enum | `inherited | confirmed | spec | wip | implemented | drift | deprecated` |
| `acceptance` | string \| null | Behavioral spec (NL or Gherkin). Test seed. |
| `contract` | string \| null | I/O types, error modes, invariants. |
| `rationale_ref` | string[] | Decision Log entry IDs that touched this node. |
| `touch_budget` | string[] \| null | File globs implementations may edit. |

## Per-edge SSOT fields

| field | type | meaning |
|---|---|---|
| `status` | enum | `inherited | confirmed | spec | implemented | drift | deprecated` |
| `rationale_ref` | string[] | Decision Log entry IDs that touched this edge. |

## Per-layer SSOT fields

| field | type | meaning |
|---|---|---|
| `status` | enum | `inherited | confirmed | spec | implemented | drift | deprecated` |
| `acceptance` | string \| null | Layer-wide invariant. |
| `rationale_ref` | string[] | Decision Log entry IDs that touched this layer. |

## Status lifecycle

```
inherited ──┬──> confirmed   (DL entry affirms current shape)
            ├──> spec        (DL entry declares new intent, code not yet matching)
            └──> deprecated  (DL entry marks for removal)

spec ──> wip ──> implemented   (code now matches SSOT, verified by ssot_diff)
                       │
                       └──> drift  (code diverged from SSOT)
```

## Defaults at seed time

Every node, edge, and layer projected from the Impl KG starts with:

```json
{
  "status": "inherited",
  "acceptance": null,
  "contract": null,
  "rationale_ref": [],
  "touch_budget": null
}
```

(Edges and layers omit fields that don't apply — see tables above.)
