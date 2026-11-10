# personas

An open-source, event-based persona engine for developers. Turn product events into user personas to deliver tailored in-product marketing experiences.

Python is the first package. TypeScript and Go will judge the same cases.

## Try it

From this repo:

```bash
spec/examples/demo/script/demo
```

Avery is blocked. Blake is a champion. Each line is a different nudge.

## Use it

```python
from plgkit_personas import track, persona

track(user_id, "created_doc")
persona(user_id)
```

Put `config.yml` and `mapping.yml` in `plgkit/personas/`. Then run `plgkit-personas migrate`.

The rules and the sample files are in [spec/README.md](spec/README.md).

[python](packages/python) · [demo](spec/examples/demo)
