"""Persistent request and token limits for paid LLM calls.

Limits are shared by every process that uses the same NFL_STATE_DIR. If the state
cannot be read or written, chat is refused rather than running without a limit.
"""
import hashlib
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import STATE_DIR

DEFAULTS = {
    "NFL_CHAT_PER_MINUTE": 5,              # one client
    "NFL_CHAT_GLOBAL_PER_MINUTE": 20,      # everyone
    "NFL_CHAT_DAILY_LIMIT": 200,           # everyone, UTC day
    "NFL_LLM_DAILY_TOKEN_LIMIT": 500_000,  # everyone, UTC day
    "NFL_LLM_MAX_OUTPUT_TOKENS": 4000,     # one provider call
}


class LimitExceeded(RuntimeError):
    """The message is safe to show to the user."""


def setting(name):
    raw = os.environ.get(name, "").strip()
    try:
        value = int(raw) if raw else DEFAULTS[name]
    except ValueError:
        raise LimitExceeded(f"{name} geçersiz; sohbet güvenlik için kapalı.") from None
    if value < 1:
        raise LimitExceeded(f"{name} en az 1 olmalıdır; sohbet güvenlik için kapalı.")
    return value


def _today():
    return datetime.now(timezone.utc).date().isoformat()


@contextmanager
def _transaction():
    con = None
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(STATE_DIR / "usage.sqlite", timeout=10, isolation_level=None)
        con.execute("BEGIN IMMEDIATE")
        con.execute("CREATE TABLE IF NOT EXISTS requests (at REAL NOT NULL, client TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS daily "
                    "(day TEXT PRIMARY KEY, chats INTEGER NOT NULL, tokens INTEGER NOT NULL)")
        yield con
        con.execute("COMMIT")
    except (OSError, sqlite3.Error) as exc:
        raise LimitExceeded("Kullanım sınırı kaydına erişilemiyor; sohbet geçici olarak kapalı.") from exc
    finally:
        if con is not None:
            con.close()  # Rolls back an unfinished transaction.


def register_chat(client_id):
    client = hashlib.sha256(str(client_id).encode()).hexdigest()[:24]
    per_client, per_minute = setting("NFL_CHAT_PER_MINUTE"), setting("NFL_CHAT_GLOBAL_PER_MINUTE")
    per_day = setting("NFL_CHAT_DAILY_LIMIT")
    now, day = time.time(), _today()
    with _transaction() as con:
        con.execute("DELETE FROM requests WHERE at <= ?", [now - 60])
        con.execute("INSERT OR IGNORE INTO daily VALUES (?, 0, 0)", [day])
        own = con.execute("SELECT count(*) FROM requests WHERE client = ?", [client]).fetchone()[0]
        everyone = con.execute("SELECT count(*) FROM requests").fetchone()[0]
        chats = con.execute("SELECT chats FROM daily WHERE day = ?", [day]).fetchone()[0]
        if own >= per_client or everyone >= per_minute:
            raise LimitExceeded("Çok sık soru gönderildi. Bir dakika sonra tekrar deneyin.")
        if chats >= per_day:
            raise LimitExceeded("Günlük soru sınırına ulaşıldı. Yarın tekrar deneyin.")
        con.execute("INSERT INTO requests VALUES (?, ?)", [now, client])
        con.execute("UPDATE daily SET chats = chats + 1 WHERE day = ?", [day])


def reserve_tokens(payload_bytes):
    """Reserve a conservative estimate before a call, so parallel calls cannot overspend."""
    amount = payload_bytes // 2 + setting("NFL_LLM_MAX_OUTPUT_TOKENS")
    limit, day = setting("NFL_LLM_DAILY_TOKEN_LIMIT"), _today()
    with _transaction() as con:
        con.execute("INSERT OR IGNORE INTO daily VALUES (?, 0, 0)", [day])
        used = con.execute("SELECT tokens FROM daily WHERE day = ?", [day]).fetchone()[0]
        if used + amount > limit:
            raise LimitExceeded("Günlük yapay zekâ kullanım bütçesi doldu. Yarın tekrar deneyin.")
        con.execute("UPDATE daily SET tokens = tokens + ? WHERE day = ?", [amount, day])
    return day, amount


def settle_tokens(reservation, actual):
    """Replace the reservation with reported usage; keep it when usage is unknown."""
    if isinstance(actual, bool) or not isinstance(actual, int) or actual < 0:
        return
    day, amount = reservation
    with _transaction() as con:
        con.execute("UPDATE daily SET tokens = max(0, tokens + ?) WHERE day = ?", [actual - amount, day])
