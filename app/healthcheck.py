"""Container health check: HTTP endpoint answers and the database is queryable."""
import os
import sys
import urllib.request

from app import analytics


def main():
    try:
        analytics.query("SELECT count(*) AS n FROM players")
        url = os.environ.get("NFL_HEALTH_URL") or f"http://127.0.0.1:{os.environ.get('PORT', '8501')}/_stcore/health"
        with urllib.request.urlopen(url, timeout=5) as response:
            return 0 if response.status == 200 else 1
    except Exception as exc:
        print(f"unhealthy: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
