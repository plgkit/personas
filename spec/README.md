# Persona contract

Watch what someone does. Sort each action into one category. Stick on the first label that fits.

Python, TypeScript, and Go implement this. They judge [the same cases](fixtures/cases.json).

## Track

`track(user_id, action, metadata)`

| Field | Required | Meaning |
|---|---|---|
| `user_id` | yes | Opaque string |
| `action` | yes | Your product's verb, such as `created_doc` |
| `metadata.occurred_at` | no | When it happened. Receipt time is used when this is missing |
| `metadata.event_id` | no | The same user and id is stored once. The first call wins |

`occurred_at` is ISO-8601 with a timezone, such as `2026-11-09T15:00:00Z` or an offset. A timestamp with no timezone is rejected. Stored times look like `2026-11-09T15:00:00.000000Z`.

Other metadata is stored as JSON and is not copied into reasons.

An action missing from the mapping is stored. It does not move the label.

`track` returns true when the row is new, and false when `event_id` was already stored.

## Files in your app

```
your-app/plgkit/personas/config.yml
your-app/plgkit/personas/mapping.yml
```

`mapping.yml` is flat. One action, one category.

| Your action | Category |
|---|---|
| `created_doc` | `core_action` |
| `sent_invite` | `invite_sent` |
| `connected_slack` | `setup_step` |

The category set is closed: `core_action`, `invite_sent`, `setup_step`.

The category is resolved when `persona()` runs. Editing the mapping recomputes history.

`config.yml` holds the policy numbers. Omitted keys use these defaults.

| Key | Default |
|---|---|
| `lookback_days` | 14 |
| `silence_days` | 7 |
| `champion_min` | 1 |
| `power_user_min` | 8 |
| `implementer_min` | 2 |
| `database_url_env` | `PLGKIT_DATABASE_URL` |

`silence_days` has to be smaller than `lookback_days`. Every number is an integer of 1 or more.

`database_url_env` is the name of the variable that holds the database address. The address stays out of the file. A `postgres://` or `postgresql://` address uses Postgres. When the variable is unset, the package uses `plgkit_events.sqlite` in the current directory. That is the same default file nudges uses. Personas writes `plgkit_persona_events`, so both packages can share one database.

`plgkit-personas migrate` creates the table. Run it again after an upgrade. It applies new numbered files only.

## Ask

`persona(user_id)` returns one object.

| Field | Meaning |
|---|---|
| `user_id` | The id you asked about |
| `persona` | The winning label |
| `reasons` | Up to 5 events that support the winner, newest first |
| `counts` | Mapped events inside the lookback: `core_action`, `invite_sent`, `setup_step` |
| `matched` | Every label whose rule is true, in the order below |
| `calculated_at` | When we judged, UTC |

A reason is `action`, `category`, and `occurred_at`.

Pass `now` to pin `calculated_at`. The same events can change label when the clock moves.

## Who wins

Only mapped events inside the lookback are counted.

| Boundary | What happens |
|---|---|
| Exactly `lookback_days` old | Counted |
| Older than the lookback | Ignored |
| After `calculated_at` | Ignored |
| Newest mapped event is exactly `silence_days` old | Quiet |
| Newer than that | Active |

First row that matches wins.

| Order | Label | Rule |
|---|---|---|
| 1 | `champion` | `invite_sent` >= `champion_min` |
| 2 | `power_user` | `core_action` >= `power_user_min` |
| 3 | `blocked` | At least one `setup_step` or `core_action`, and quiet |
| 4 | `implementer` | `setup_step` >= `implementer_min` |
| 5 | `evaluator` | Any mapped event in the window |
| 6 | `unknown` | No mapped event in the window |

Reasons that support each winner:

| Winner | Events cited |
|---|---|
| `champion` | `invite_sent` |
| `power_user` | `core_action` |
| `blocked` | Any mapped event |
| `implementer` | `setup_step` |
| `evaluator` | Any mapped event |
| `unknown` | None |

Ties on the same timestamp use the action name, then the order the events were given. Newest first, then a later name, then a later event.

## Two users

Judged at `2026-11-10T15:00:00Z`.

| Person | History | Label | Nudge in the demo |
|---|---|---|---|
| Avery | 3 setup steps, newest 9 days ago | `blocked` | Want help with the step you stopped on? |
| Blake | 10 core actions in the last week, plus 1 invite yesterday | `champion` | Bring in the person you invited. |

The package does not choose nudge copy. The [demo](examples/demo) does.

## Sample result

Avery:

```json
{
  "user_id": "avery",
  "persona": "blocked",
  "reasons": [
    {
      "action": "picked_template",
      "category": "setup_step",
      "occurred_at": "2026-11-01T15:00:00.000000Z"
    },
    {
      "action": "created_workspace",
      "category": "setup_step",
      "occurred_at": "2026-10-31T15:00:00.000000Z"
    },
    {
      "action": "connected_slack",
      "category": "setup_step",
      "occurred_at": "2026-10-30T15:00:00.000000Z"
    }
  ],
  "counts": {"core_action": 0, "invite_sent": 0, "setup_step": 3},
  "matched": ["blocked", "implementer", "evaluator"],
  "calculated_at": "2026-11-10T15:00:00.000000Z"
}
```

The full reason list and the rest of the cases live in [fixtures/cases.json](fixtures/cases.json).
