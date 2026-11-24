import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal

from app import analytics
from app.assistant import answer
from app.config import DB
from app.observability import configure_logging

configure_logging()
logger = logging.getLogger("nfl.api")
app = FastAPI(title="NFL Dataset Assistant", version="0.1.0")


@app.middleware("http")
async def handle_unexpected_error(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("api_unexpected_error", extra={"event": "api_unexpected_error", "error_type": type(exc).__name__})
        return JSONResponse(status_code=500, content={"detail": "İşlem tamamlanamadı. Lütfen daha sonra tekrar deneyin."})


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=12000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[Message] = Field(default_factory=list, max_length=12)


@app.get("/health")
def health():
    return {"status": "ok", "database_ready": DB.exists()}


@app.get("/dataset")
def dataset():
    return analytics.dataset_summary()


@app.get("/players")
def players(name: str):
    return analytics.search_players(name)


@app.get("/players/{player_id}")
def player(player_id: int):
    return analytics.player_profile(player_id)


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        return answer(request.question, [m.model_dump() for m in request.history])
    except ValueError as exc:
        logger.warning("chat_request_rejected", extra={"event": "chat_request_rejected", "error_type": type(exc).__name__})
        raise HTTPException(400, str(exc)) from exc
    except httpx.TimeoutException as exc:
        logger.warning("chat_provider_timeout", extra={"event": "chat_provider_timeout", "error_type": type(exc).__name__})
        raise HTTPException(504, "Sohbet sağlayıcısı zamanında yanıt vermedi. Biraz sonra tekrar deneyin.") from exc
    except FileNotFoundError as exc:
        logger.warning("chat_dataset_unavailable", extra={"event": "chat_dataset_unavailable", "error_type": type(exc).__name__})
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        logger.warning("chat_provider_unavailable", extra={"event": "chat_provider_unavailable", "error_type": type(exc).__name__})
        raise HTTPException(502, "Dil modeli servisine erişilemedi. Sağlayıcı ayarlarını kontrol edin.") from exc
