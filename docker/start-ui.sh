#!/bin/sh
exec python -m streamlit run app/ui.py --server.address=0.0.0.0 --server.port="${PORT:-8501}" \
    --server.headless=true --browser.gatherUsageStats=false --client.showErrorDetails=none \
    --client.toolbarMode=minimal --server.fileWatcherType=none
