"""Run one credential-safe, real-provider chat smoke test against the local DB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

from app import analytics
from app.assistant import answer
from app.config import DB


def main():
    if not os.environ.get("NFL_LLM_API_KEY", "").strip():
        raise SystemExit("NFL_LLM_API_KEY is not set; no provider request was sent.")
    if not os.environ.get("NFL_LLM_MODEL", "").strip():
        raise SystemExit("NFL_LLM_MODEL is not set; no provider request was sent.")
    if not DB.exists():
        raise SystemExit(f"Local database not found at {DB}; no provider request was sent.")

    candidates = analytics.query("""
        SELECT p.display_name, g.season
        FROM player_play pp
        JOIN players p USING (nfl_id)
        JOIN games g USING (game_id)
        WHERE g.season_type = 'REG'
        GROUP BY p.display_name, g.season
        ORDER BY g.season DESC, p.display_name
        LIMIT 1
    """)
    if not candidates:
        raise SystemExit("No player with a regular-season record was found; no provider request was sent.")

    player = candidates[0]
    question = (
        f"{player['display_name']} oyuncusunun {player['season']} normal sezonunda "
        "kayıtlı maç sayısını ve sack toplamını özetle; eksik bilgiyi belirt."
    )
    result = answer(question)
    print("Provider smoke test: completed")
    print(f"Question scope: player={player['display_name']}; season={player['season']}; type=REG")
    print("Answer:")
    print(result["answer"])
    print("Evidence:")
    for item in result["evidence"]:
        payload = item.get("result", {})
        print({
            "tool": item.get("tool"),
            "sources": payload.get("sources", []),
            "rows": len(payload.get("data", [])) if isinstance(payload.get("data"), list) else None,
            "scope": payload.get("scope", {}),
        })


if __name__ == "__main__":
    main()
