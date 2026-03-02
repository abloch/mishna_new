#!/bin/bash
`cat .env.json | jq -r 'to_entries | map(. | "export " + .key + "=" + (.value | tostring)) | join("\n")'`
uv run python main.py .env.json
