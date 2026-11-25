import json
import sqlite3
import threading

import duckdb
import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app import analytics, api, assistant, config, healthcheck, limits
from pipelines import backup, demo_data, ingest


@pytest.fixture
def demo(tmp_path, monkeypatch):
    path = tmp_path / "curated" / "nfl.duckdb"
    for module in (analytics, api, backup, config, ingest):
        monkeypatch.setattr(module, "DB", path)
    monkeypatch.setattr(backup, "STATE_DIR", limits.STATE_DIR)
    demo_data.ensure()
    return path


def test_demo_is_deterministic_fictional_and_labelled(demo):
    assert demo_data.rows() == demo_data.rows()
    catalog = json.loads((demo.parent / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["demo"] is True and "SENTETİK" in catalog["source"]
    with duckdb.connect(str(demo), read_only=True) as con:
        assert con.execute("SELECT count(*) FROM players WHERE display_name NOT LIKE 'Kurgusal %'").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM player_play WHERE team_abbr NOT LIKE 'DEMO-%'").fetchone()[0] == 0
    payload = analytics.player_performance([900001, 900007], 2025, "REG")
    assert payload["kind"] == "synthetic_demo"
    assert payload["coverage_notes"][0] == analytics.DEMO_NOTE
    assert len(payload["data"]) == 2
    assert analytics.team_summary("DEMO-A", 2025)["data"]
    assert "KURGUSAL DEMO" in assistant.provenance_line([{"result": payload}])


def test_demo_rerun_is_noop_and_old_demo_version_is_replaced(demo, monkeypatch):
    before = demo.stat().st_mtime_ns
    demo_data.ensure()
    assert demo.stat().st_mtime_ns == before
    monkeypatch.setattr(demo_data, "SOURCE", "SENTETİK DEMO v2")
    demo_data.ensure()
    assert analytics.dataset_summary()["provenance"]["source"] == "SENTETİK DEMO v2"


@pytest.mark.parametrize("catalog", [None, {"source": "real"}])
def test_demo_never_overwrites_other_database(demo, catalog):
    path = demo.parent / "catalog.json"
    path.unlink()
    if catalog:
        path.write_text(json.dumps(catalog), encoding="utf-8")
    before = demo.read_bytes()
    with pytest.raises(SystemExit, match="üzerine yazılmadı"):
        demo_data.ensure()
    assert demo.read_bytes() == before


def test_demo_ui_runs_and_hides_research(demo, monkeypatch):
    monkeypatch.delenv("NFL_LLM_API_KEY", raising=False)
    monkeypatch.setattr(analytics, "research_snapshot", lambda: pytest.fail("research must stay hidden"))
    app = AppTest.from_file(str(config.ROOT / "app" / "ui.py"), default_timeout=30).run()
    assert not app.exception
    assert analytics.DEMO_NOTE in [item.value for item in app.warning]
    assert not any("Gözlenen veriler" in item.value for item in app.caption)
    assert any("sağlayıcısı yapılandırılmamış" in item.value for item in app.info)


def test_readiness_and_healthcheck(demo, monkeypatch):
    client = TestClient(api.app)
    assert client.get("/ready").json() == {"status": "ready", "demo": True}
    monkeypatch.setenv("NFL_HEALTH_URL", "http://127.0.0.1:1/")
    assert healthcheck.main() == 1
    demo.unlink()
    assert client.get("/ready").status_code == 503


def test_client_global_and_daily_limits(monkeypatch):
    monkeypatch.setenv("NFL_CHAT_PER_MINUTE", "1")
    monkeypatch.setenv("NFL_CHAT_GLOBAL_PER_MINUTE", "2")
    monkeypatch.setenv("NFL_CHAT_DAILY_LIMIT", "3")
    now = [1000.0]
    monkeypatch.setattr(limits.time, "time", lambda: now[0])
    limits.register_chat("a")
    with pytest.raises(limits.LimitExceeded, match="sık"):
        limits.register_chat("a")
    limits.register_chat("b")
    with pytest.raises(limits.LimitExceeded, match="sık"):
        limits.register_chat("c")
    now[0] += 61
    limits.register_chat("a")
    now[0] += 61
    with pytest.raises(limits.LimitExceeded, match="Günlük soru"):
        limits.register_chat("a")
    monkeypatch.setattr(limits, "_today", lambda: "2999-01-01")
    limits.register_chat("a")


def test_parallel_reservations_never_exceed_budget(monkeypatch):
    monkeypatch.setenv("NFL_LLM_MAX_OUTPUT_TOKENS", "100")
    monkeypatch.setenv("NFL_LLM_DAILY_TOKEN_LIMIT", "300")
    outcomes = []

    def reserve():
        try:
            limits.reserve_tokens(0)
            outcomes.append("reserved")
        except limits.LimitExceeded as exc:
            outcomes.append(str(exc))

    threads = [threading.Thread(target=reserve) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count("reserved") == 3
    assert sum("bütçesi" in item for item in outcomes) == 5


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_invalid_limit_disables_chat(monkeypatch, value):
    monkeypatch.setenv("NFL_CHAT_DAILY_LIMIT", value)
    with pytest.raises(limits.LimitExceeded, match="kapalı"):
        limits.register_chat("a")


def test_unwritable_state_disables_chat(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setattr(limits, "STATE_DIR", blocker / "state")
    with pytest.raises(limits.LimitExceeded, match="kapalı"):
        limits.register_chat("a")


def used_tokens():
    con = sqlite3.connect(limits.STATE_DIR / "usage.sqlite")
    try:
        return con.execute("SELECT tokens FROM daily").fetchone()[0]
    finally:
        con.close()


@pytest.mark.parametrize("response,expected", [
    (httpx.Response(200, json={"usage": {"total_tokens": 42}}), 42),
    (httpx.Response(401, json={"error": {"message": "no"}}), 0),
])
def test_provider_usage_settles_and_output_is_capped(response, expected):
    sent = []

    class Client:
        def post(self, url, headers, json):
            sent.append(json)
            return response

    try:
        assistant.limited_completion(Client(), "https://example.test", "k", {"model": "m"})
    except ValueError:
        assert expected == 0
    assert sent[0]["max_tokens"] == limits.DEFAULTS["NFL_LLM_MAX_OUTPUT_TOKENS"]
    assert used_tokens() == expected


def test_unknown_usage_or_timeout_keeps_conservative_reservation():
    class NoUsage:
        def post(self, *args, **kwargs):
            return httpx.Response(200, json={})

    class Timeout:
        def post(self, *args, **kwargs):
            raise httpx.ReadTimeout("slow")

    assistant.limited_completion(NoUsage(), "https://example.test", "k", {})
    first = used_tokens()
    assert first >= limits.DEFAULTS["NFL_LLM_MAX_OUTPUT_TOKENS"]
    with pytest.raises(httpx.ReadTimeout):
        assistant.limited_completion(Timeout(), "https://example.test", "k", {})
    assert used_tokens() == 2 * first


def test_exhausted_budget_blocks_provider_and_api_returns_429(monkeypatch):
    monkeypatch.setenv("NFL_LLM_API_KEY", "k")
    monkeypatch.setenv("NFL_LLM_MODEL", "m")
    monkeypatch.setenv("NFL_LLM_DAILY_TOKEN_LIMIT", "1")
    monkeypatch.setattr(assistant, "request_completion", lambda *a: pytest.fail("provider was called"))
    response = TestClient(api.app).post("/chat", json={"question": "Soru"})
    assert response.status_code == 429
    assert "bütçesi" in response.json()["detail"]


def test_backup_restore_round_trip(demo, tmp_path):
    limits.register_chat("a")
    archive = tmp_path / "backup.zip"
    backup.create(archive)
    original = demo.read_bytes()
    with pytest.raises(ValueError, match="zaten var"):
        backup.create(archive)
    demo.write_bytes(b"corrupt")
    (limits.STATE_DIR / "usage.sqlite").unlink()
    backup.restore(archive)
    assert demo.read_bytes() == original
    assert analytics.query("SELECT count(*) AS n FROM players")[0]["n"] == 48
    con = sqlite3.connect(limits.STATE_DIR / "usage.sqlite")
    assert con.execute("SELECT chats FROM daily").fetchone()[0] == 1
    con.close()


def test_corrupt_backup_leaves_current_database_untouched(demo, tmp_path):
    archive = tmp_path / "backup.zip"
    backup.create(archive)
    original = demo.read_bytes()
    archive.write_bytes(archive.read_bytes()[:200])
    with pytest.raises(ValueError, match="bozuk"):
        backup.restore(archive)
    assert demo.read_bytes() == original
