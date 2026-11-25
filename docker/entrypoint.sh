#!/bin/sh
set -eu
if [ "${NFL_DEMO_MODE:-0}" = "1" ]; then
    python -m pipelines.demo_data
fi
exec "$@"
