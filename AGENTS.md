# Instructions for coding agents

Read this before changing this repo.

- The contract is [spec/README.md](spec/README.md). Change behavior only when the task asks for it.
- Python is the reference package. TypeScript (`packages/node`) and Go (`packages/go`) must match [spec/fixtures/cases.json](spec/fixtures/cases.json).
- Nudge copy stays in [spec/examples/nudges/messages](spec/examples/nudges/messages). The package returns a persona and reasons. Audience checks live beside those messages and call `persona()`.
- Names: Python `plgkit_personas`, npm `@plgkit/personas`, Go `github.com/plgkit/personas/packages/go`, CLI `plgkit-personas`.
- Personas uses the table `plgkit_persona_events` and its own migrations table, so it can share a database with nudges.
- Prefer fast unit tests. The demo is `spec/examples/demo/script/demo`. Do not leave it running.
