# Security Policy

MediClear AI processes potentially sensitive medical text. We take security and
privacy seriously and welcome responsible disclosure.

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting
([Security → Report a vulnerability](https://github.com/Thijsn04/MediClear-AI/security/advisories/new))
or email the maintainer. Include:

- a description of the issue and its impact,
- steps to reproduce (a proof-of-concept if possible),
- affected version/commit.

We aim to acknowledge reports within 5 business days and to ship a fix or
mitigation as quickly as severity warrants.

## Handling patient data (PHI)

MediClear is a self-hosted tool; the operator is the data controller. To reduce
risk when handling PHI:

- **Keep data on-prem.** Point `AI_PROVIDER=openai` at a local Ollama/vLLM
  server (`OPENAI_BASE_URL`) so document content never leaves your network.
- **Enable `ZERO_RETENTION=true`** so no document text, summary, or chat history
  is stored server-side. (Follow-up chat is disabled in this mode.)
- **Front the API with authentication** (`REQUIRE_API_KEY=true`) and TLS.
- **Restrict CORS** (`ALLOWED_ORIGINS`) to your own origins.
- Document content is never written to logs; only metadata (sizes, provider,
  language) is recorded for audit.

## Scope

This project is an educational aid, not a medical device. It must not be relied
on for clinical decision-making. See the disclaimer in the README.
