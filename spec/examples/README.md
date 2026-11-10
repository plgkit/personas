# Examples

Copy these files into your app.

```
your-app/plgkit/personas/personas.yml
your-app/plgkit/personas/config.yml
```

`personas.yml` names the personas, their priority, and their criteria. The sample file defines `developer`, `billing_admin`, `champion`, `blocked`, and `member`.

`config.yml` belongs beside it. The packages find `plgkit/personas/config.yml` from the current working directory.

```yaml
database_url_env: PLGKIT_DATABASE_URL
```

Set `PLGKIT_DATABASE_URL` to a `sqlite:///` or `postgres://` address. Leave it unset to use `plgkit_events.sqlite` in the current directory.

Then create the tables and calculate:

```bash
plgkit-personas migrate
plgkit-personas calculate
```

From this repo, the other two packages are:

```bash
node --experimental-strip-types packages/node/src/cli.ts migrate
go run ./packages/go/cmd/plgkit-personas migrate
```

```python
from plgkit_personas import calculate, identify, persona, persona_is, track

track(user_id, "app_opened", {"occurred_at": "2026-11-09T15:00:00Z"})
identify(user_id, {"role": "member"})
calculate()
persona(user_id)
persona_is(user_id, "developer")
```

The [demo](demo) seeds Avery and Blake, calculates, and asks nudges which line to print.

To show a line from a stored persona, copy [nudges/audiences.py](nudges/audiences.py) (or the `.ts` / `.go` file) next to your nudge messages, and copy the two files in [nudges/messages](nudges/messages) into `plgkit/nudges/messages/`.

| Message | Shown when | Line |
|---|---|---|
| `20261110150400-home-blocked-help` | `persona_is(user_id, "blocked")` | Want help with the step you stopped on? |
| `20261110150401-home-champion-invite` | `persona_is(user_id, "champion")` | Bring in the person you invited. |
