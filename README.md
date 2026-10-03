# Which parts of a ModelScope endpoint are actually authenticated?

**Finding: `GET /v1/models` returns `200` whether your token is valid or not. It is a
public catalogue. A successful model listing proves nothing about your credential —
only `POST /v1/chat/completions` exercises it.**

Measured against the two ModelScope inference hosts, with a real token, a bogus token,
and no token.

```
python3 verify.py     # writes evidence/auth_probes.json + evidence/findings.json
```

## Probes and observed codes

| probe | token | HTTP |
|-------|-------|------|
| `GET  /v1/models` | none | `200` |
| `GET  /v1/models` | bogus | `200` |
| `POST /v1/chat/completions` | bogus | `401` |
| `POST /v1/chat/completions` | real, `api-inference.modelscope.ai` | `200` |
| `POST /v1/chat/completions` | real, `api-inference.modelscope.cn` | `401` |

## What this cost me, and why it is worth writing down

I lost time on a false negative. `GET /v1/models` returned `200`, so I concluded the
credential was fine and started debugging the request body. It was not fine, and the body
was never the problem: the listing endpoint ignores the `Authorization` header entirely.

The control that settles it is the **bogus-token probe**. If a request with a deliberately
invalid token returns the same code as your real token, that endpoint is not testing your
auth at all.

## Gotchas

1. **Model listing is not an auth check.** Use a `chat/completions` probe with a known-good
   token if you want to prove a credential works.
2. **Host matters.** The `.cn` host rejected the same token that the `.ai` host accepted
   with `200`. Pin the host explicitly; do not assume they are interchangeable.
3. **Keep a negative control in your smoke test.** A bogus-token probe costs one request
   and prevents an entire class of "it says 200 so it must be fine" debugging.

## Honest caveats

- This characterises two hosts at one point in time. Endpoint auth behaviour can change;
  re-run `verify.py` rather than trusting this table indefinitely.
- `200` on `.ai` means the request was accepted, not that the account has generation
  quota. Entitlement and authentication are separate failures and look different: an
  unauthenticated request is `401`, whereas an account-level problem can still authenticate.
- Only these three probes were run. Other routes on these hosts may differ.

## Files

- `verify.py` — probe harness; reads the credential from env or the secret file, never logs it
- `evidence/auth_probes.json` — raw status codes and response heads
- `evidence/findings.json` — the four booleans the probes establish
- `receipts.sha256` — hashes of harness and evidence
