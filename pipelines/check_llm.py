"""Diagnose provider access without printing credentials or requesting paid generations."""
import os
from urllib.parse import urlparse

import httpx

from app.assistant import check_response


def main():
    key = os.environ.get("NFL_LLM_API_KEY", "").strip()
    model = os.environ.get("NFL_LLM_MODEL", "").strip()
    base = os.environ.get("NFL_LLM_BASE_URL", "").strip().rstrip("/")
    if not key or not model or not base:
        print("Eksik ortam ayarı. Anahtarı tanımladığınız PowerShell penceresinde çalıştırın.")
        return
    print(f"Sunucu: {urlparse(base).hostname}")
    print(f"Model: {model}")
    print("Anahtar: tanımlı (gizlendi)")
    print("Proxy ortam ayarı:", any(os.environ.get(k) for k in
                                     ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]))
    for label, path in [("Model listesi", "/models")]:
        try:
            response = httpx.get(base + path, headers={"Authorization": f"Bearer {key}"}, timeout=30)
            check_response(response, key)
            models = response.json().get("data", [])
            ids = [m.get("id", "") for m in models]
            print(f"{label}: başarılı")
            normalized_ids = {item.removeprefix("models/") for item in ids}
            print("Seçilen model listede:", model.removeprefix("models/") in normalized_ids)
            print("Erişilebilir modeller:", ", ".join(ids))
            for entry in models:
                if entry.get("id", "").removeprefix("models/") == model.removeprefix("models/"):
                    for field in ("capabilities", "pricing", "context_length"):
                        if field in entry:
                            print(f"{field}: {entry[field]}")
        except (ValueError, httpx.HTTPError) as exc:
            print(str(exc).replace(key, "[GİZLİ]"))


if __name__ == "__main__":
    main()
