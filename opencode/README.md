# OpenCode

This directory is a CyberGym agent adapter, not only an OpenCode installer. The
host-side runner generates a unique CyberGym task, mounts it read-write at
`/workspace`, runs OpenCode non-interactively, and stores the JSON event stream
and OpenCode session data with the benchmark logs.

OpenCode is pinned to `1.18.13` by default. The runner accepts both OpenCode's
native `provider/model` form and bare OpenAI/Anthropic model names.

## Build the image

```bash
bash opencode/install.sh
```

To build another pinned version or image tag:

```bash
OPENCODE_VERSION=1.18.13 \
IMAGE_NAME=cybergym/opencode:1.18.13 \
bash opencode/install.sh
```

## Run CyberGym

```bash
export OPENAI_API_KEY=sk-...
export CYBERGYM_DATA_DIR=/path/to/cybergym-data
export OUT_DIR=/path/to/output
export MODEL=openai/gpt-4.1
export SERVER_IP=127.0.0.1
export SERVER_PORT=8000
export TASK_ID=...

python3 opencode/run.py \
    --image_name cybergym/opencode:latest \
    --model "$MODEL" \
    --log_dir "$OUT_DIR/logs" \
    --tmp_dir "$OUT_DIR/tmp" \
    --data_dir "$CYBERGYM_DATA_DIR" \
    --task_id "$TASK_ID" \
    --server "http://$SERVER_IP:$SERVER_PORT" \
    --timeout 1200 \
    --max_iter 100 \
    --difficulty level1
```

Use `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or
`OPENROUTER_API_KEY` with the corresponding provider-prefixed model. For an API
gateway compatible with that provider, also pass `--base_url`.

Each run creates `<task-id>-<agent-id>/` under `--log_dir` containing:

- `args.json`: CyberGym task and runner metadata.
- `opencode.json`: the exact non-interactive agent configuration.
- `trajectory.jsonl`: OpenCode's machine-readable event stream.
- `console.log`: OpenCode diagnostics and errors.
- `data/`, `state/`, and `cache/`: OpenCode's session/runtime artifacts.

The generated task directory is removed by default. Pass `--remove_tmp false`
to retain it for debugging.

The host-side runner must be executed in a CyberGym Python environment with
the `docker` and `simple-parsing` packages installed. Project-level OpenCode
configuration from the generated task directory is disabled so that each run
uses the recorded `opencode.json` reproducibly.
