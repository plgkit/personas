# personas

An open-source, event-based persona engine for developers. Turn product events into user personas to deliver tailored in-product marketing experiences.

Python, TypeScript, and Go judge the same cases.

## Try it

From this repo:

```bash
spec/examples/demo/script/demo
spec/examples/demo/script/demo --backend node
spec/examples/demo/script/demo --backend go
```

Avery is blocked. Blake is a champion. Each line comes from a nudge file.

## Use it

```python
from plgkit_personas import track, persona

track(user_id, "created_doc")
persona(user_id)
```

```ts
import { track, persona } from "@plgkit/personas";
```

```go
import plgkit "github.com/plgkit/personas/packages/go"
```

Put `config.yml` and `mapping.yml` in `plgkit/personas/`. Then run `plgkit-personas migrate`.

The rules and the sample files are in [spec/README.md](spec/README.md).

[python](packages/python) · [node](packages/node) · [go](packages/go) · [demo](spec/examples/demo)
