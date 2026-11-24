# Test, performance, and error handling

## Reproducible local setup

Use Python 3.11 (the same version as CI) and install the development dependencies:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check --select E4,E7,E9,F app/analytics.py app/api.py app/assistant.py app/config.py app/observability.py app/ui.py tests scripts/measure_player_directory.py
```

To run the application, prepare the local dataset with `python -m pipelines.ingest`, then start Streamlit with `streamlit run app/ui.py`. The database defaults to `data/curated/nfl.duckdb`; set `NFL_DB_PATH` to use another DuckDB file. Chat credentials are configured through environment variables described in `docs/LLM_KURULUMU.md` and are never emitted in logs.

GitHub Actions runs the same test and Ruff commands on pull requests. Runtime dependencies keep bounded supported-version ranges in `requirements-app.txt`; Ruff is pinned in `requirements-dev.txt` so local and CI lint rules use the same release.

## Player directory performance

The original player screen loaded the full directory and filtered it in Python. The new screen sends search, position, and draft filters to DuckDB and requests 100 rows at a time. Query results are cached by the resolved database path, modification timestamp, file size, SQL, and parameters. Replacing or rebuilding the database changes the cache key.

Baseline and updated measurements use `python scripts/measure_player_directory.py`. The script builds a temporary 10,000-player database and reports the median of seven cold searches for `Player 099`:

| Path | Median response | Rows loaded | Matches |
| --- | ---: | ---: | ---: |
| Full directory, then Python filter | 114.53 ms | 10,000 | 100 |
| SQL filter and 100-row page, cold | 58.08 ms | 100 | 100 |
| Same page with warm cache | 0.79 ms | 100 | 100 |

This run used Python 3.12.7, DuckDB 1.5.6, and Streamlit 1.37.1 on the development machine. Treat the timings as a repeatable synthetic baseline, not a production dataset or hosted-browser benchmark. The acceptance goals are: first filtered page under 200 ms at 10,000 synthetic players, no more than 100 player rows transferred per page, and unchanged-version repeat searches served from cache. Re-run the script after data or query changes; use the real curated dataset and browser instrumentation before making production latency claims.

## Logs and user errors

Application logs are newline-delimited JSON with event name, severity, and exception type. They intentionally omit exception messages, SQL values, request contents, and credentials. The UI and API return short, actionable messages; unexpected API failures use a generic response while retaining a safe event in server logs.
