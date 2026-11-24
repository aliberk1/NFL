import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from app import analytics
from app.assistant import answer
from app.config import DB

app = FastAPI(title="NFL Dataset Assistant", version="0.1.0")


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
        raise HTTPException(400, str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Sohbet sağlayıcısı zamanında yanıt vermedi. Biraz sonra tekrar deneyin.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Dil modeli servisine erişilemedi. Sağlayıcı ayarlarını kontrol edin.") from exc
