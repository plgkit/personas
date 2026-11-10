# Instructions for coding agents

Read this before changing this repo.

- The contract is [spec/README.md](spec/README.md). Change behavior only when the task asks for it.
- Python is the reference package. TypeScript (`packages/node`) and Go (`packages/go`) must match [spec/fixtures/cases.json](spec/fixtures/cases.json).
- Nudge copy stays in [spec/examples/nudges/messages](spec/examples/nudges/messages). The package stores a persona and reasons. Audience checks are written by hand and call `persona_is`.
- Names: Python `plgkit_personas`, npm `@plgkit/personas`, Go `github.com/plgkit/personas/packages/go`, CLI `plgkit-personas`.
- Personas uses `plgkit_persona_events`, `plgkit_persona_traits`, and `plgkit_persona_snapshots`, plus its own migrations table, so it can share a database with nudges.
- `persona()` reads the snapshot. `calculate` is what judges. Persona names live only in `personas.yml`.
- Prefer fast unit tests. The demo is `spec/examples/demo/script/demo`. Do not leave it running.
