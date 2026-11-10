# Persona nudges

Two messages. Copy them into `your-app/plgkit/nudges/messages/`.

Copy one audience file next to them:

| App | File |
|---|---|
| Python | [audiences.py](audiences.py) |
| TypeScript | [audiences.ts](audiences.ts) |
| Go | [audiences.go](audiences.go) |

| Message | `audience.require_all` | Line |
|---|---|---|
| `20261110150400-home-blocked-help` | `persona_is_blocked` | Want help with the step you stopped on? |
| `20261110150401-home-champion-invite` | `persona_is_champion` | Bring in the person you invited. |

Those two functions are written by hand. Each one calls `persona_is` with `blocked` or `champion`. Run `plgkit-personas calculate` before the page asks nudges what to show. A stored persona with any other name matches neither function, so these two messages stay hidden.
