# Optional ai-ready toolkit

Read this only when the toolkit is already available in the environment.

Use it only if already available and helpful. Pass the target explicitly:

```text
ai-ready audit /absolute/target --json
ai-ready adopt /absolute/target
```

From a bootstrapped toolkit checkout, use
`uv run --project /absolute/toolkit ai-ready audit /absolute/target --json`.
Audit describes configuration, not proven correctness, and may not recognize all
native conventions. Adoption previews changes; `adopt --apply` creates files and
belongs only in authorized implementation. The toolkit's `ai-ready verify` invokes
the target's `make verify`; use native verification directly when that target does
not exist. Do not install the toolkit or execute reference commands just because
this skill mentions them.
