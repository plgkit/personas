# personas

Define personas in a file. Record what people do. A scheduled command stores who matches.

Python, TypeScript, and Go judge the same cases.

## Get started

1. Write `plgkit/personas/personas.yml`. Each persona has a name, a priority, and criteria. A lower priority number wins. The same number uses the earlier persona in the file.

```yaml
groups:
  app_use:
    - app_opened
    - session_started

personas:
  - name: developer
    priority: 1
    require_all:
      - count:
          group: app_use
          at_least: 3
          within_days: 3
    exclude:
      - trait:
          key: role
          equals: billing_admin
  - name: billing_admin
    priority: 2
    require_all:
      - trait:
          key: role
          equals: billing_admin
```

2. Add `config.yml` at `plgkit/personas/config.yml`, under the directory you start the app from. Python, TypeScript, and Go look for that path in the current working directory. `migrate` and `calculate` do too, which is why the cron example below starts with `cd /app`.

```
your-app/plgkit/personas/config.yml
your-app/plgkit/personas/personas.yml
```

The file has one key. `database_url_env` is the name of the environment variable that holds the database address.

```yaml
database_url_env: PLGKIT_DATABASE_URL
```

```bash
export PLGKIT_DATABASE_URL="sqlite:///plgkit_events.sqlite"
```

| Value of `PLGKIT_DATABASE_URL` | Database |
|---|---|
| Unset | `plgkit_events.sqlite` in the current directory |
| `sqlite:///path/to/file.sqlite` | That SQLite file |
| `postgres://...` or `postgresql://...` | Postgres |

A missing `config.yml` uses the variable name `PLGKIT_DATABASE_URL`. To use another name, change `database_url_env` and set that variable. Any other key in the file is an error. The sample file is [spec/examples/config.yml](spec/examples/config.yml).

3. Create the tables, then record events and traits.

```bash
plgkit-personas migrate
```

```python
from plgkit_personas import identify, persona, persona_is, track

track(user_id, "app_opened")
identify(user_id, {"role": "member"})
```

4. Calculate on a schedule. The command judges everyone who has events or traits and stores one row each. Run it from the directory that contains `plgkit/personas/config.yml`.

```bash
plgkit-personas calculate
```

```cron
15 2 * * * cd /app && plgkit-personas calculate
```

5. Read the stored row. `persona` does not judge live. `persona_is` is true only when the stored winner is that name.

```python
persona(user_id)
persona_is(user_id, "developer")
```

A nudge audience is a function you write. It calls `persona_is`. See [spec/examples/nudges](spec/examples/nudges).

The contract, the criteria keys, and the sample result are in [spec/README.md](spec/README.md).

## Try the demo

```bash
spec/examples/demo/script/demo
spec/examples/demo/script/demo --backend node
spec/examples/demo/script/demo --backend go
```

| Person | Persona | Line |
|---|---|---|
| Avery | blocked | Want help with the step you stopped on? |
| Blake | champion | Bring in the person you invited. |

[python](packages/python) · [node](packages/node) · [go](packages/go) · [demo](spec/examples/demo)
