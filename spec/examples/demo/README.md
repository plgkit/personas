# Demo

Two users, two nudges.

From the repo root:

```bash
spec/examples/demo/script/demo
spec/examples/demo/script/demo --backend node
spec/examples/demo/script/demo --backend go
```

| Person | Label | Line |
|---|---|---|
| Avery | blocked | Want help with the step you stopped on? |
| Blake | champion | Bring in the person you invited. |

The events come from [cases.json](../../fixtures/cases.json). The demo calls `calculate`, then `persona`, then nudges `decide()`. The sentences come from the nudge files in [../nudges/messages](../nudges/messages). The audience checks call `persona_is`.

The demo downloads [nudges](https://github.com/plgkit/nudges) at commit `db82c8caba8309266ef0b8cd39d98d9fb4f89e35` into `~/.cache/plgkit-nudges/`. Set `PLGKIT_NUDGES_ROOT` to use a checkout you already have. A private checkout uses `gh auth token` when that command works.
