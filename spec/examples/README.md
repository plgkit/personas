# Examples

Copy this folder into your app.

```
your-app/plgkit/personas/config.yml
your-app/plgkit/personas/mapping.yml
```

`config.yml` holds the window, the thresholds, and the name of the database variable.

`mapping.yml` turns your verbs into `core_action`, `invite_sent`, and `setup_step`.

Then create the table:

```bash
plgkit-personas migrate
```

From this repo, the other two packages are:

```bash
node --experimental-strip-types packages/node/src/cli.ts migrate
go run ./packages/go/cmd/plgkit-personas migrate
```

```python
from plgkit_personas import track, persona

track(user_id, "created_doc", {"occurred_at": "2026-11-09T15:00:00Z"})
persona(user_id)
```

The [demo](demo) seeds Avery and Blake and prints a nudge for each.
