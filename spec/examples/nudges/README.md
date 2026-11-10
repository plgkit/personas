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

`evaluator`, `implementer`, `power_user`, and `unknown` match neither name, so these two messages stay hidden.

The functions call `persona()` for `ctx.user.id`. In an app, `plgkit/personas/mapping.yml` and `config.yml` are picked up from the working directory.
