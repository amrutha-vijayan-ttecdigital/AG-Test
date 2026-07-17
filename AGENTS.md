# AGENTS.md - CX Agent Studio Starter Kit Rules

Read `.agents/AGENTS.md` before making implementation changes. That file is the
project-level source of truth for CX Agent Studio architecture, callback rules,
handoff conventions, and visual design verification.

Do not run live Google Cloud, Lucid, Jira, or deployment workflows until
`./setup.sh` succeeds. A local `.env` with placeholder values, missing gcloud
auth, missing ADC, or a mismatched active gcloud account is not considered
onboarded.

The `.env` file is local-only and ignored by Git. Never commit credentials,
tokens, generated client config, or local caches.
