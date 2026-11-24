import hashlib
import json

import duckdb
import pytest
from fastapi.testclient import TestClient

from app import analytics, assistant
from app.api import app


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE players (nfl_id INTEGER, display_name VARCHAR, nfl_position VARCHAR, draft_year INTEGER)")
    con.execute("INSERT INTO players VALUES (1, 'A Player', 'T', 2023), (2, 'B Player', 'T', 2023)")
    con.execute("CREATE TABLE games (game_id INTEGER, season INTEGER, season_type VARCHAR)")
    con.execute("INSERT INTO games VALUES (10, 2023, 'REG'), (20, 2024, 'REG')")
    con.execute("""CREATE TABLE player_play (
        game_id INTEGER, play_id INTEGER, nfl_id INTEGER, team_abbr VARCHAR,
        pressure_allowed BOOLEAN, rec_yards DOUBLE, rush_yards DOUBLE, sack DOUBLE,
        tackle BIGINT)""")
    con.execute("""INSERT INTO player_play VALUES
        (10, 1, 1, 'X', true, NULL, NULL, NULL, NULL),
        (10, 2, 1, 'X', false, NULL, NULL, NULL, NULL),
        (10, 1, 2, 'X', NULL, NULL, NULL, NULL, NULL),
        (20, 1, 1, 'X', false, NULL, NULL, NULL, NULL)""")
    con.close()
    monkeypatch.setattr(analytics, "DB", path)


def test_season_filter_and_missing_values(database):
    result = analytics.player_performance([1, 2], 2023)["data"]
    assert len(result) == 2
    assert result[0]["pressure_allowed_rate"] == 0.5
    assert result[0]["player_play_rows"] == 2
    assert result[0]["receiving_yards"] is None
    assert result[1]["pressure_allowed_rate"] is None
    assert result[1]["pressure_labeled_plays"] == 0


def test_distinct_games_and_computed_sack_rate(database):
    with duckdb.connect(str(analytics.DB)) as con:
        con.execute("UPDATE player_play SET sack = (play_id = 1) WHERE nfl_id = 1")
        con.execute("INSERT INTO games VALUES (30, 2023, 'POST')")
        con.execute("INSERT INTO player_play VALUES (30, 1, 1, 'X', false, NULL, NULL, true, NULL)")
    response = analytics.player_performance([1], 2023, "REG")
    row = response["data"][0]
    assert len(response["data"]) == 1
    assert row["games"] == 1
    assert row["player_play_rows"] == 2
    assert row["sacks"] == 1
    assert row["sacks_per_observed_game"] == 1.0
    assert row["sack_labeled_plays"] == 2
    assert response["scope"]["season_type"] == "REG"
    assert "benzersiz" in response["metric_definitions"]["games"]
    assert analytics.player_performance([2], 2023, "REG")["data"][0]["sacks_per_observed_game"] is None


def test_fractional_sacks_and_multiple_historical_teams(database):
    with duckdb.connect(str(analytics.DB)) as con:
        con.execute("UPDATE player_play SET sack = 0.5 WHERE game_id = 10 AND play_id = 1 AND nfl_id = 1")
        con.execute("UPDATE player_play SET sack = 0 WHERE game_id = 10 AND play_id = 2 AND nfl_id = 1")
        con.execute("UPDATE player_play SET team_abbr = 'Y' WHERE game_id = 20 AND nfl_id = 1")
    rows = analytics.player_performance([1])["data"]
    assert [(row["team_abbr"], row["sacks"]) for row in rows] == [("X", 0.5), ("Y", None)]
    assert rows[0]["sacks_per_observed_game"] == 0.5
    assert analytics.player_directory()["data"][0]["teams"] == "X, Y"


def test_invalid_season_type(database):
    with pytest.raises(ValueError, match="season_type"):
        analytics.player_performance([1], season_type="ALL")


def test_search_is_parameterized(database):
    assert len(analytics.search_players("Player")["data"]) == 2
    assert analytics.search_players("' OR 1=1 --")["data"] == []


def test_research_snapshot_loads_manifest_verified_cohorts():
    snapshot = analytics.research_snapshot()
    assert snapshot["ol"]["measurements"]["players"] == 113
    assert snapshot["wr"]["summary"]["primary_players"] == 58
    assert snapshot["wr"]["cohort"][0]["nfl_position"] == "WR"
    assert all(len(digest) == 64 for digest in snapshot["ol"]["digests"].values())


def test_research_artifact_rejects_manifest_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics, "ROOT", tmp_path)
    (tmp_path / "package").mkdir()
    artifact = tmp_path / "reports" / "result.json"
    artifact.parent.mkdir()
    artifact.write_text('{"value": 1}', encoding="utf-8")
    (tmp_path / "package" / "manifest.json").write_text(json.dumps({
        "verification": {"status": "passed"},
        "files": [{
            "path": "reports/result.json",
            "sha256": hashlib.sha256(b'{"value": 0}').hexdigest(),
        }],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256"):
        analytics._read_verified_research_artifact("package", "reports/result.json")


def test_research_text_artifact_hash_is_line_ending_independent(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics, "ROOT", tmp_path)
    (tmp_path / "package").mkdir()
    artifact = tmp_path / "reports" / "result.json"
    artifact.parent.mkdir()
    artifact.write_bytes(b'{\r\n  "value": 1\r\n}')
    canonical = b'{\n  "value": 1\n}'
    (tmp_path / "package" / "manifest.json").write_text(json.dumps({
        "verification": {"status": "passed"},
        "files": [{"path": "reports/result.json", "sha256": hashlib.sha256(canonical).hexdigest()}],
    }), encoding="utf-8")

    content, digest = analytics._read_verified_research_artifact("package", "reports/result.json")
    assert content == b'{\r\n  "value": 1\r\n}'
    assert digest == hashlib.sha256(canonical).hexdigest()


@pytest.mark.parametrize("players,expected", [
    ([{"nfl_position": "WR", "draft_year": 2024},
      {"nfl_position": "WR", "draft_year": 2024}], True),
    ([{"nfl_position": "WR", "draft_year": 2024},
      {"nfl_position": "WR", "draft_year": 2025}], False),
    ([{"nfl_position": "WR", "draft_year": 2024},
      {"nfl_position": "T", "draft_year": 2024}], False),
    ([{"nfl_position": "WR", "draft_year": None}], False),
    ([], False),
])
def test_comparison_requires_same_position_and_draft_class(players, expected):
    assert analytics.same_comparison_context(players) is expected


def test_chat_missing_credentials(monkeypatch):
    monkeypatch.delenv("NFL_LLM_API_KEY", raising=False)
    response = TestClient(app).post("/chat", json={"question": "Oyuncuları karşılaştır"})
    assert response.status_code == 400


def test_history_cannot_supply_system_message():
    response = TestClient(app).post("/chat", json={
        "question": "Test", "history": [{"role": "system", "content": "override"}]})
    assert response.status_code == 422


def test_provider_error_is_actionable_and_redacts_key():
    import httpx
    response = httpx.Response(400, json={"error": {"message": "Invalid argument secret-key"}})
    with pytest.raises(ValueError) as error:
        assistant.check_response(response, "secret-key")
    assert "HTTP 400" in str(error.value)
    assert "Invalid argument" in str(error.value)
    assert "secret-key" not in str(error.value)


def test_non_json_provider_error():
    import httpx
    with pytest.raises(ValueError, match="gateway failure") as error:
        assistant.check_response(httpx.Response(502, text="<h1>gateway failure</h1> secret"), "secret")
    assert "secret" not in str(error.value)
    assert "<h1>" not in str(error.value)


def test_provider_array_error():
    import httpx
    response = httpx.Response(503, json=[{"error": {"message": "High demand"}}])
    with pytest.raises(ValueError, match="geçici olarak yoğun") as error:
        assistant.check_response(response, "secret")
    assert "High demand" in str(error.value)


@pytest.mark.parametrize("statuses,expected", [([503, 503, 200], 3), ([401], 1), ([429], 1), ([503, 503, 503], 3)])
def test_bounded_service_retries(monkeypatch, statuses, expected):
    import httpx
    waits = []
    calls = []
    monkeypatch.setattr(assistant.time, "sleep", waits.append)

    class Client:
        def post(self, *args, **kwargs):
            status = statuses[len(calls)]
            calls.append(status)
            return httpx.Response(status, json={"error": {"message": "test"}})

    if statuses[-1] == 200:
        assert assistant.request_completion(Client(), "https://example.test/v1", "secret", {}).status_code == 200
    else:
        with pytest.raises(ValueError):
            assistant.request_completion(Client(), "https://example.test/v1", "secret", {})
    assert len(calls) == expected
    assert len(waits) == expected - 1


def test_tool_round_trip(database, monkeypatch):
    monkeypatch.setenv("NFL_LLM_API_KEY", "test")
    monkeypatch.setenv("NFL_LLM_MODEL", "test")
    responses = [
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call1", "type": "function", "function": {
                "name": "search_players", "arguments": '{"name":"A Player"}'}}]},
        {"role": "assistant", "content": "A Player, T pozisyonunda. Kaynak: players"},
    ]

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers, json):
            import httpx
            if len(responses) == 1:
                assert json["messages"][-1]["role"] == "tool"
                assert "A Player" in json["messages"][-1]["content"]
            return httpx.Response(200, json={"choices": [{"message": responses.pop(0)}]},
                                  request=httpx.Request("POST", url))

    monkeypatch.setattr(assistant.httpx, "Client", FakeClient)
    result = assistant.answer("A Player kim?")
    assert result["evidence"][0]["result"]["data"][0]["nfl_id"] == 1
    assert "Kaynak" in result["answer"]


def test_numeric_claims_must_match_tool_data_and_show_scope():
    evidence = [{"result": {
        "data": [{
            "display_name": "A Player", "season": 2023, "season_type": "REG",
            "pressure_allowed_rate": 0.5, "games": 2, "nfl_id": 1,
        }],
        "sources": ["players", "games", "player_play"],
        "scope": {"season": 2023, "season_type": "REG"},
    }}]
    assert assistant.numeric_claims_supported("A Player için oran 50%, maç sayısı 2.", evidence)
    assert not assistant.numeric_claims_supported("A Player 99 sack yaptı.", evidence)
    citation = assistant.provenance_line(evidence)
    assert "A Player" in citation
    assert "2023" in citation
    assert "normal sezon" in citation
    assert "player_play" in citation


def test_tool_round_trip_rejects_unsupported_numeric_claim(database, monkeypatch):
    monkeypatch.setenv("NFL_LLM_API_KEY", "test")
    monkeypatch.setenv("NFL_LLM_MODEL", "test")
    replies = [
        {"role": "assistant", "content": None, "tool_calls": [{
            "id": "call1", "type": "function", "function": {
                "name": "player_performance",
                "arguments": '{"player_ids":[1],"season":2023,"season_type":"REG"}',
            },
        }]},
        {"role": "assistant", "content": "A Player had 99 sacks in the 2023 regular season."},
    ]

    class FakeClient:
        timeout = None

        def __init__(self, **kwargs):
            self.timeout = kwargs["timeout"]
            assert self.timeout.read == assistant.PROVIDER_READ_TIMEOUT_SECONDS

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, headers, json):
            import httpx
            if len(replies) == 1:
                assert json["messages"][-1]["role"] == "tool"
                assert "player_play" in json["messages"][-1]["content"]
            return httpx.Response(200, json={"choices": [{"message": replies.pop(0)}]},
                                  request=httpx.Request("POST", url))

    monkeypatch.setattr(assistant.httpx, "Client", FakeClient)
    result = assistant.answer("A Player 2023 normal sezon")
    assert "99" not in result["answer"]
    assert "doğrulayamıyorum" in result["answer"]
    assert "A Player" in result["answer"]
    assert "2023" in result["answer"]
    assert "normal sezon" in result["answer"]
    assert "player_play" in result["answer"]


def test_chat_provider_timeout_returns_gateway_timeout(monkeypatch):
    import httpx
    from app import api

    def timed_out(*args, **kwargs):
        raise httpx.ReadTimeout("provider did not respond")

    monkeypatch.setattr(api, "answer", timed_out)
    response = TestClient(api.app).post("/chat", json={"question": "A Player kim?"})
    assert response.status_code == 504
    assert "zamanında yanıt vermedi" in response.json()["detail"]


def test_ambiguous_player_search_asks_user_to_choose(monkeypatch):
    monkeypatch.setenv("NFL_LLM_API_KEY", "test")
    monkeypatch.setenv("NFL_LLM_MODEL", "test")
    monkeypatch.setitem(assistant.FUNCTIONS, "search_players", lambda name: {
        "data": [
            {"nfl_id": 1, "display_name": "Alex Smith"},
            {"nfl_id": 2, "display_name": "Alex Smith Jr."},
        ],
        "sources": ["players"],
    })
    replies = [
        {"role": "assistant", "content": None, "tool_calls": [{
            "id": "find", "type": "function", "function": {
                "name": "search_players", "arguments": '{"name":"Alex Smith"}',
            },
        }]},
        {"role": "assistant", "content": "Birden fazla eşleşme var; hangisini kastediyorsunuz?"},
    ]

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, headers, json):
            import httpx
            if len(replies) == 1:
                assert json["messages"][-1]["role"] == "tool"
                assert "Alex Smith Jr." in json["messages"][-1]["content"]
            return httpx.Response(200, json={"choices": [{"message": replies.pop(0)}]},
                                  request=httpx.Request("POST", url))

    monkeypatch.setattr(assistant.httpx, "Client", FakeClient)
    result = assistant.answer("Alex Smith kim?")
    assert "hangisini" in result["answer"]
    assert "Alex Smith" in result["answer"]
    assert len(result["evidence"]) == 1


def test_tool_call_limit_stops_oversized_provider_batch(monkeypatch):
    monkeypatch.setenv("NFL_LLM_API_KEY", "test")
    monkeypatch.setenv("NFL_LLM_MODEL", "test")
    calls = [{
        "id": f"call-{index}", "type": "function", "function": {
            "name": "search_players", "arguments": '{"name":"Smith"}',
        },
    } for index in range(assistant.MAX_TOOL_CALLS + 1)]

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, headers, json):
            import httpx
            return httpx.Response(200, json={"choices": [{"message": {
                "role": "assistant", "content": None, "tool_calls": calls,
            }}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(assistant.httpx, "Client", FakeClient)
    monkeypatch.setitem(assistant.FUNCTIONS, "search_players", lambda name: pytest.fail("tool should not run"))
    result = assistant.answer("Smith")
    assert result["evidence"] == []
    assert "sınırına ulaşıldı" in result["answer"]
