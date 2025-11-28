#!/bin/sh
# Substitute environment variables in litellm config template using sed
sed "s|\${VLLM_API_BASE}|${VLLM_API_BASE}|g" /app/config.yaml.template > /app/config.yaml

# Start LiteLLM with the processed config
exec litellm --config /app/config.yaml --port 4000 --host 0.0.0.0 --detailed_debug
