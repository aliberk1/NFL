import pytest

from app import limits


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Tests must never read or change the developer's usage counters."""
    monkeypatch.setattr(limits, "STATE_DIR", tmp_path / "state")
    for name in (*limits.DEFAULTS, "NFL_LLM_MAX_TOKENS_FIELD"):
        monkeypatch.delenv(name, raising=False)
