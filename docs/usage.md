# Usage Guide

This guide covers three audiences:

1. [Patients / end users](#1-using-the-web-ui) using the built-in web UI.
2. [Integrators](#2-using-the-api) calling the REST API from their own code.
3. [Operators](#3-operating-the-service) running and tuning the service.

Try everything instantly with no API key:

```bash
AI_PROVIDER=demo uvicorn app.main:app
# open http://localhost:8000
```

---

## 1. Using the web UI

Open the app in a browser (default `http://localhost:8000`).

1. **Choose an input method.** Paste text, or switch to *Upload file* and drop a
   PDF, JPEG, PNG, or WEBP (photos of letters work well; scanned PDFs are OCR'd
   when OCR is enabled).
2. **Pick a reading level.** *Simplest* (A2), *Standard* (B1), or *Detailed*
   (B2). This controls how plainly the explanation is written.
3. **Pick a response language.** 17 languages are supported.
4. **Select Simplify document.** You get a structured explanation: a summary, a
   plain-language explanation, any lab values and medications found, key medical
   terms with definitions, and practical next steps.
5. **Ask follow-up questions** in the chat box. Answers stream in and are
   grounded in your original document.
6. **Listen** reads the explanation aloud; **Print** produces a clean printout
   with the medical disclaimer.

Use the header controls to switch the interface language and toggle light/dark.

---

## 2. Using the API

Base path `/api/v1`. Interactive docs live at `/api/docs`. When
`REQUIRE_API_KEY=true`, send `X-API-Key: <key>` (or `Authorization: Bearer
<key>`) on every request.

### Analyse a document (structured result)

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: $KEY" \
  -F "text=The patient presents with acute myocardial infarction." \
  -F "language=en" -F "reading_level=B1"
```

The response contains a structured `analysis` object, a `markdown` convenience
string, a `session_id` for follow-ups, and provider/model metadata. See
[api.md](api.md) for the full schema.

Upload a file instead of text:

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: $KEY" \
  -F "file=@discharge_summary.pdf" -F "language=nl"
```

### Follow-up chat (streaming)

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/$SESSION/stream \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"message": "Should I be worried?", "language": "en"}'
```

### Python

```python
import httpx

BASE = "http://localhost:8000/api/v1"
headers = {"X-API-Key": "your-key"}  # omit if REQUIRE_API_KEY is false

with httpx.Client() as client:
    r = client.post(
        f"{BASE}/analyze",
        headers=headers,
        data={"text": "Patient has type 2 diabetes mellitus.", "language": "en",
              "reading_level": "B1"},
    )
    r.raise_for_status()
    result = r.json()
    print(result["analysis"]["summary"])
    for term in result["analysis"]["key_terms"]:
        print(f"- {term['term']}: {term['definition']} [{term['source']}]")

    session = result["session_id"]
    chat = client.post(
        f"{BASE}/chat/{session}",
        headers=headers,
        json={"message": "What does this mean for my diet?", "language": "en"},
    )
    print(chat.json()["response"])
```

### JavaScript / TypeScript (with streaming)

```js
const BASE = "http://localhost:8000/api/v1";
const headers = { "X-API-Key": "your-key" };

// Analyse
const form = new FormData();
form.append("text", "Patient has hypertension.");
form.append("language", "en");
form.append("reading_level", "B1");
const res = await fetch(`${BASE}/analyze`, { method: "POST", headers, body: form });
const data = await res.json();
console.log(data.analysis.summary);

// Stream a follow-up (Server-Sent Events)
const stream = await fetch(`${BASE}/chat/${data.session_id}/stream`, {
  method: "POST",
  headers: { ...headers, "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Is this serious?", language: "en" }),
});
const reader = stream.body.getReader();
const decoder = new TextDecoder();
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  for (const line of decoder.decode(value).split("\n")) {
    if (line.startsWith("data:")) {
      const evt = JSON.parse(line.slice(5));
      if (evt.delta) process.stdout.write(evt.delta);
    }
  }
}
```

### Errors and rate limits

Every error uses one envelope: `{"error", "status_code", "request_id"}`. A `429`
includes a `Retry-After` header. Each response echoes an `X-Request-ID` you can
use when reporting problems.

---

## 3. Operating the service

- **Choose a provider.** Set `AI_PROVIDER` and the matching key/model. Any
  OpenAI-compatible server works via `AI_PROVIDER=openai` + `OPENAI_BASE_URL`
  (Ollama, Azure, Groq, vLLM, LM Studio). See [configuration.md](configuration.md).
- **Protect it.** Turn on `REQUIRE_API_KEY` with `API_KEYS`, restrict
  `ALLOWED_ORIGINS`, and keep the rate limiter on.
- **Scale it.** Set `REDIS_URL` so sessions, cache, and rate limits are shared
  across instances. The Helm chart and `docker-compose.prod.yml` wire this up.
- **Watch it.** `GET /api/v1/health` reports provider and session-store status;
  `/metrics` exposes Prometheus request and token-usage counters.
- **PHI / air-gapped.** Point the provider at a local model, set
  `TTS_BACKEND=local`, keep `TERMINOLOGY_ONLINE=false`, and enable
  `ZERO_RETENTION=true` so nothing derived from the document is stored. The
  frontend has no external dependencies, so it works fully offline.

See [deploy/README.md](../deploy/README.md) for Docker, Compose, Helm, and Nginx
walkthroughs.
