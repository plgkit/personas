# Persona contract

You name the personas. The engine stores events and traits, then a calculate command writes one winner per person.

Python, TypeScript, and Go implement this. They judge [the same cases](fixtures/cases.json).

## Files

```
your-app/plgkit/personas/personas.yml
your-app/plgkit/personas/config.yml
```

`personas.yml` is the only place persona names exist. A missing file means nobody matches.

`config.yml` has one key.

| Key | Default | Meaning |
|---|---|---|
| `database_url_env` | `PLGKIT_DATABASE_URL` | Name of the variable that holds the database address |

The address stays out of the file. A `postgres://` or `postgresql://` address uses Postgres. When the variable is unset, the package uses `plgkit_events.sqlite` in the current directory. Personas writes its own tables, so it can share that file with nudges.

Unknown config keys are an error.

## Track and identify

`track(user_id, action, metadata)`

| Field | Required | Meaning |
|---|---|---|
| `user_id` | yes | Opaque string |
| `action` | yes | Your product's verb, such as `app_opened` |
| `metadata.occurred_at` | no | When it happened. Receipt time is used when this is missing |
| `metadata.event_id` | no | The same user and id is stored once. The first call wins |

`occurred_at` is ISO-8601 with a timezone, such as `2026-11-09T15:00:00Z`. A timestamp with no timezone is rejected. Stored times look like `2026-11-09T15:00:00.000000Z`.

Other metadata is stored as JSON and is not copied into reasons.

`track` returns true when the row is new, and false when `event_id` was already stored.

`identify(user_id, traits)` stores the latest string for each key. Traits have no history. `{"role": "member"}` is valid. An empty object or a non-string value is an error.

## Criteria

Each persona has `name`, `priority`, and any of `require_all`, `require_one_of`, and `exclude`.

| Key | Passes when |
|---|---|
| `require_all` | Every condition is true. Omitted or empty passes |
| `require_one_of` | At least one condition is true. Omitted passes. Present and empty fails |
| `exclude` | No condition is true. Omitted or empty excludes nobody |

Omitting all three matches everyone. When nothing matches, the stored persona is an empty string.

A condition is a `count` or a `trait`. Lists do not nest.

| Count field | Meaning |
|---|---|
| `action`, `actions`, or `group` | Exactly one of these. `group` names a list under `groups` |
| `at_least` | Required integer of 0 or more |
| `at_most` | Optional integer, at least `at_least` |
| `within_days` | Required integer of 1 or more |

A day is 24 hours. An event counts when `now - within_days * 24h <= occurred_at <= now`. The exact boundary counts. A later event is ignored.

A trait condition is `key` and `equals`, both strings. A missing trait does not equal that value, so an `exclude` of `role: billing_admin` keeps someone who has no role.

`priority` is a required integer. Lower wins. The same number uses the earlier persona in the file.

## Calculate

`plgkit-personas calculate` judges every user who has events or traits and stores one row.

```bash
plgkit-personas calculate
plgkit-personas calculate --user ada
plgkit-personas calculate --now 2026-11-10T15:00:00Z
```

The summary line is `Calculated N users. M assigned. U unmatched.`

There is no daemon. The app's scheduler runs the command. Node and Go expose the same command.

`plgkit-personas migrate` creates the tables. Run it again after an upgrade. It applies new numbered files only.

## Read

`persona(user_id)` reads the stored row. It does not judge.

| Field | Meaning |
|---|---|
| `user_id` | The id you asked about |
| `persona` | The stored winner, or `""` when nobody matched |
| `matched` | Every name whose criteria were true, best priority first |
| `reasons` | Up to 5 reasons for the winner |
| `calculated_at` | When calculate ran, UTC, or `""` before the first row |

Before the first calculate, every field except `user_id` is empty. A missing table raises an error that mentions migrate.

`persona_is(user_id, name)` is true only when the stored winner equals `name`. An empty name is an error. An empty stored persona is not a match.

Reasons come from true `require_all` and true `require_one_of` conditions. Exclude conditions are not reasons. Events come first, newest first, then a later action name, then a later input. Trait reasons follow, in condition order. The same event is cited once. The cap is 5.

| Kind | Fields |
|---|---|
| `event` | `action`, `occurred_at` |
| `trait` | `key`, `equals` |

## Sample

Judged at `2026-11-10T15:00:00.000000Z` with [spec/examples/personas.yml](examples/personas.yml).

| Person | History | Winner |
|---|---|---|
| Avery | 3 setup steps, newest 9 days ago | `blocked` |
| Blake | docs plus one invite on Nov 9 | `champion` |

Avery:

```json
{
  "user_id": "avery",
  "persona": "blocked",
  "matched": ["blocked"],
  "reasons": [
    {"kind": "event", "action": "picked_template", "occurred_at": "2026-11-01T15:00:00.000000Z"},
    {"kind": "event", "action": "created_workspace", "occurred_at": "2026-10-31T15:00:00.000000Z"},
    {"kind": "event", "action": "connected_slack", "occurred_at": "2026-10-30T15:00:00.000000Z"}
  ],
  "calculated_at": "2026-11-10T15:00:00.000000Z"
}
```

The rest of the cases live in [fixtures/cases.json](fixtures/cases.json). The [demo](examples/demo) prints a nudge line for Avery and Blake. The package does not choose that copy.
