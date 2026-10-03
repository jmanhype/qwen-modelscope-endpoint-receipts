"""Which parts of the ModelScope endpoint are actually authenticated?

Getting this wrong costs an afternoon: `GET /v1/models` returns 200 whether or
not your token is valid, so a successful model listing proves nothing about
your credential. This script records the HTTP codes that distinguish the two.

Never prints the credential.
"""
from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request

from qwen_client import MODEL, load_key

HERE = pathlib.Path(__file__).parent
AI_HOST = "https://api-inference.modelscope.ai/v1"
CN_HOST = "https://api-inference.modelscope.cn/v1"
BOGUS = "ms-00000000-0000-0000-0000-000000000000"


def probe(name: str, url: str, *, token: str | None, method: str = "GET", body=None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode()
            code = resp.status
    except urllib.error.HTTPError as exc:
        raw, code = exc.read().decode(), exc.code
    except Exception as exc:
        raw, code = f"{type(exc).__name__}: {exc}", 0
    return {
        "probe": name,
        "url": url,
        "method": method,
        "token": "none" if token is None else ("bogus" if token == BOGUS else "real"),
        "http_status": code,
        "body_head": raw[:240].replace("\n", " "),
    }


CHAT_BODY = {"model": MODEL, "messages": [{"role": "user", "content": "hi"}],
             "max_tokens": 4, "stream": False}


def main() -> int:
    key = load_key()
    probes = [
        probe("models_no_auth", f"{AI_HOST}/models", token=None),
        probe("models_bogus_token", f"{AI_HOST}/models", token=BOGUS),
        probe("chat_bogus_token", f"{AI_HOST}/chat/completions", token=BOGUS,
              method="POST", body=CHAT_BODY),
        probe("chat_real_token_ai", f"{AI_HOST}/chat/completions", token=key,
              method="POST", body=CHAT_BODY),
        probe("chat_real_token_cn", f"{CN_HOST}/chat/completions", token=key,
              method="POST", body=CHAT_BODY),
    ]

    for p in probes:
        print(f"{p['probe']:<22} token={p['token']:<6} http={p['http_status']}")

    out = HERE / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "auth_probes.json").write_text(
        json.dumps({"model": MODEL, "probes": probes}, indent=2) + "\n"
    )

    by = {p["probe"]: p["http_status"] for p in probes}
    findings = {
        "models_listing_is_public": by["models_no_auth"] == 200 and by["models_bogus_token"] == 200,
        "chat_requires_valid_token": by["chat_bogus_token"] == 401,
        "ai_host_accepts_real_token": by["chat_real_token_ai"] == 200,
        "cn_host_rejects_real_token": by["chat_real_token_cn"] != 200,
    }
    (out / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    print("\n=== findings ===")
    print(json.dumps(findings, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
