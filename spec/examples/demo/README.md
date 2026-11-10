# Demo

Two users, two nudges.

From the repo root:

```bash
spec/examples/demo/script/demo
spec/examples/demo/script/demo --backend node
spec/examples/demo/script/demo --backend go
```

| Person | Label | Line |
|---|---|---|
| Avery | blocked | Want help with the step you stopped on? |
| Blake | champion | Bring in the person you invited. |

The events come from [cases.json](../../fixtures/cases.json). The nudge lines live in the script. The package only returns the label and the reasons.
