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

2. Create the tables, then record events and traits.

```bash
plgkit-personas migrate
```

```python
from plgkit_personas import identify, persona, persona_is, track

track(user_id, "app_opened")
identify(user_id, {"role": "member"})
```

3. Calculate on a schedule. The command judges everyone who has events or traits and stores one row each.

```bash
plgkit-personas calculate
```

```cron
15 2 * * * cd /app && plgkit-personas calculate
```

4. Read the stored row. `persona` does not judge live. `persona_is` is true only when the stored winner is that name.

```python
persona(user_id)
persona_is(user_id, "developer")
```

A nudge audience is a function you write. It calls `persona_is`. See [spec/examples/nudges](spec/examples/nudges).

`config.yml` only names the environment variable that holds the database address. The sample is [spec/examples/config.yml](spec/examples/config.yml).

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
