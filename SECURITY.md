# Security

## Dependency Audit

### Backend (pip-audit)

Audited against `backend/requirements.txt` — **0 known vulnerabilities** found.

Run again:
```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```

### Frontend (npm audit)

Audited production dependencies — **0 vulnerabilities** found.

Run again:
```bash
cd frontend && npm audit --omit=dev
```

---

## PII Redaction

User input is scanned and redacted **before** it reaches the LLM. Patterns covered:

| Category | Pattern |
|----------|---------|
| Greek tax number (AFM) | 9-digit sequences |
| Greek social security (AMKA) | 11-digit sequences |
| Email addresses | RFC 5322-style regex |
| Greek phone numbers | +30 / 00 30 / 69x / 2x formats |

Redaction is logged by count only (no content is stored). See `backend/security/pii.py`.

---

## Prompt Injection Hardening

The ReAct system prompt contains explicit safety clauses instructing the agent to refuse:
- Requests to reveal the system prompt or instructions
- Role-override instructions ("forget you are…", "act as DAN…")
- Tasks outside procurement domain

Three injection test cases are in `evals/golden_set.json` (IDs `q14`, `q15`, `q16`).

---

## Rate Limiting

- `POST /chat` — 10 requests/minute per IP
- All other endpoints — 30 requests/minute per IP

Returns HTTP 429 with JSON body on limit exceeded.

---

## CORS

Allowed origins are sourced from the `ALLOWED_ORIGINS` environment variable (comma-separated). No wildcard (`*`) is used in production.

---

## Secrets Management

- Never commit `.env` files. Add to `.gitignore`.
- Use `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MONGODB_URI` as environment variables or secrets manager entries.
- The `.env.example` file provides a template with no real values.

---

## Known Accepted Risks

| Risk | Mitigation |
|------|-----------|
| No auth on API endpoints | Intended for internal/demo use; add OAuth2/API key middleware before public exposure |
| ChromaDB stored on local disk | Data at rest not encrypted; use encrypted volumes in production |
| OpenAI API key used for embeddings | Rotated per environment; never logged |
