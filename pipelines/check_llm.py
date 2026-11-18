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
            print("Seçilen model listede:", model in ids)
            print("Flash modeller:", ", ".join(m for m in ids if "flash" in m.lower()))
        except (ValueError, httpx.HTTPError) as exc:
            print(str(exc).replace(key, "[GİZLİ]"))


if __name__ == "__main__":
    main()
