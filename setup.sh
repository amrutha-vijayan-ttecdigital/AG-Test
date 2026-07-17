#!/usr/bin/env bash
# CX Agent Studio Onboarding Setup Script
# Collects connection details, verifies local auth prerequisites, and generates .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
VERIFY_ONLY=0

usage() {
  cat <<'EOF'
Usage:
  ./setup.sh             Interactive onboarding; writes .env and verifies auth
  ./setup.sh --verify    Verify the existing .env and local Google auth only
  ./setup.sh --help      Show this help
EOF
}

for arg in "$@"; do
  case "$arg" in
    --verify)
      VERIFY_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

load_env() {
  if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: No .env found at $ENV_FILE" >&2
    echo "Run ./setup.sh first." >&2
    exit 1
  fi

  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
}

require_value() {
  local name="$1"
  local value="${!name:-}"
  if [ -z "$value" ]; then
    echo "ERROR: $name is required in $ENV_FILE" >&2
    return 1
  fi
  case "$value" in
    your-*|your.*|*@domain.com|xxxxxxxx*|*.example.com)
      echo "ERROR: $name still contains a template value: $value" >&2
      return 1
      ;;
  esac
}

verify_core_config() {
  local failures=0

  require_value GCP_PROJECT_ID || failures=1
  require_value GCP_REGION || failures=1
  require_value DEVELOPER_EMAIL || failures=1

  if ! command -v gcloud >/dev/null 2>&1; then
    echo "ERROR: gcloud CLI is not installed." >&2
    echo "Install it from https://cloud.google.com/sdk/docs/install" >&2
    return 1
  fi
  echo "  OK gcloud CLI: $(command -v gcloud)"

  local active_account
  active_account="$(gcloud config get-value account 2>/dev/null || true)"
  if [ -z "$active_account" ]; then
    echo "ERROR: No active gcloud account is configured." >&2
    echo "Run: gcloud auth login --account=\"$DEVELOPER_EMAIL\"" >&2
    failures=1
  elif [ "$active_account" != "$DEVELOPER_EMAIL" ]; then
    echo "ERROR: Active gcloud account '$active_account' does not match DEVELOPER_EMAIL '$DEVELOPER_EMAIL'." >&2
    echo "Run: gcloud auth login --account=\"$DEVELOPER_EMAIL\"" >&2
    failures=1
  else
    echo "  OK active gcloud account: $active_account"
  fi

  if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    echo "ERROR: Application Default Credentials are missing or invalid." >&2
    echo "Run: gcloud auth application-default login --account=\"$DEVELOPER_EMAIL\"" >&2
    failures=1
  else
    echo "  OK Application Default Credentials"
  fi

  if ! gcloud projects describe "$GCP_PROJECT_ID" >/dev/null 2>&1; then
    echo "ERROR: Could not access GCP project '$GCP_PROJECT_ID' with the active account." >&2
    failures=1
  else
    echo "  OK GCP project access: $GCP_PROJECT_ID"
  fi

  if [ -n "${LUCID_API_KEY:-${LUCID_TOKEN:-}}" ]; then
    echo "  OK Lucid token present"
  else
    echo "  NOTE Lucid token not set. Lucid export/read/convert skills will fail until LUCID_API_KEY or LUCID_TOKEN is added to .env."
  fi

  if [ -n "${JIRA_USER:-}" ] || [ -n "${JIRA_TOKEN:-}" ] || [ -n "${JIRA_SITE:-}" ] || [ -n "${JIRA_PROJECT:-}" ]; then
    if [ -z "${JIRA_USER:-}" ] || [ -z "${JIRA_TOKEN:-}" ] || [ -z "${JIRA_SITE:-}" ] || [ -z "${JIRA_PROJECT:-}" ]; then
      echo "ERROR: Jira configuration is partial. Set JIRA_SITE, JIRA_USER, JIRA_TOKEN, and JIRA_PROJECT, or leave all blank." >&2
      failures=1
    else
      echo "  OK Jira credentials present"
    fi
  else
    echo "  NOTE Jira credentials not set. Design-audit Jira scans will fail until Jira variables are added to .env."
  fi

  if [ -n "${PRACTITEST_API_KEY:-}" ] || [ -n "${PRACTITEST_PROJECT_ID:-}" ] || [ -n "${PRACTITEST_FILTER_ID:-}" ] || [ -n "${PRACTITEST_EMAIL:-}" ]; then
    if [ -z "${PRACTITEST_API_KEY:-}" ] || [ -z "${PRACTITEST_PROJECT_ID:-}" ] || [ -z "${PRACTITEST_FILTER_ID:-}" ] || [ -z "${PRACTITEST_EMAIL:-}" ]; then
      echo "ERROR: PractiTest configuration is partial. Set PRACTITEST_API_KEY, PRACTITEST_PROJECT_ID, PRACTITEST_FILTER_ID, and PRACTITEST_EMAIL, or leave all blank." >&2
      failures=1
    else
      echo "  OK PractiTest credentials present"
    fi
  else
    echo "  NOTE PractiTest credentials not set. PractiTest skills will fail until PractiTest variables are added to .env."
  fi

  return "$failures"
}

echo "============================================================"
echo "    Google Cloud CX Agent Studio: Onboarding & Setup"
echo "============================================================"
echo ""

if [ "$VERIFY_ONLY" -eq 1 ]; then
  load_env
  echo "Verifying existing .env and local auth..."
  echo ""
  if verify_core_config; then
    echo ""
    echo "Setup verification passed."
    exit 0
  fi
  echo ""
  echo "Setup verification failed. Fix the errors above and run ./setup.sh --verify again." >&2
  exit 1
fi

# --- Create or overwrite .env ---
if [ -f "$ENV_FILE" ]; then
  echo "⚠️  An existing .env file was found at:"
  echo "    $ENV_FILE"
  echo ""
  read -rp "  Overwrite existing configuration? [y/N]: " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
    echo "  Aborted setup. Existing configuration preserved."
    exit 0
  fi
  echo ""
fi

echo "Please enter your project and developer details:"
echo ""

# 1. GCP Project ID (Force input)
GCP_PROJECT_ID=""
while [ -z "$GCP_PROJECT_ID" ]; do
  read -rp "👉 GCP Project ID (required): " GCP_PROJECT_ID
done

# 2. GCP Region
read -rp "👉 GCP Region [us]: " GCP_REGION
GCP_REGION="${GCP_REGION:-us}"

# 3. Developer Email (Force input)
DEVELOPER_EMAIL=""
while [ -z "$DEVELOPER_EMAIL" ]; do
  read -rp "👉 Developer Email (required): " DEVELOPER_EMAIL
done

# 4. CES Agent ID (Optional)
read -rp "👉 CX Agent/App ID (UUID, optional): " CES_AGENT_ID

# 5. Optional integrations
echo ""
echo "Optional integrations. Leave blank to skip; add them to .env later if needed."
read -rsp "👉 Lucid API key/token (optional): " LUCID_API_KEY
echo ""
read -rp "👉 Jira username/email (optional): " JIRA_USER
if [ -n "$JIRA_USER" ]; then
  read -rsp "👉 Jira API token: " JIRA_TOKEN
  echo ""
  read -rp "👉 Jira site/domain (e.g. your-domain.atlassian.net): " JIRA_SITE
  read -rp "👉 Jira project key (e.g. PROJ): " JIRA_PROJECT
else
  JIRA_TOKEN=""
  JIRA_SITE=""
  JIRA_PROJECT=""
fi

read -rp "👉 PractiTest email (optional): " PRACTITEST_EMAIL
if [ -n "$PRACTITEST_EMAIL" ]; then
  read -rsp "👉 PractiTest API token/key: " PRACTITEST_API_KEY
  echo ""
  read -rp "👉 PractiTest project ID: " PRACTITEST_PROJECT_ID
  read -rp "👉 PractiTest default filter ID: " PRACTITEST_FILTER_ID
else
  PRACTITEST_API_KEY=""
  PRACTITEST_PROJECT_ID=""
  PRACTITEST_FILTER_ID=""
fi

# Detect OS to select default TTS engine (saves API costs on macOS)
if [ "$(uname)" = "Darwin" ]; then
  DEFAULT_TTS="say"
else
  DEFAULT_TTS="google"
fi

# Write details to .env
cat > "$ENV_FILE" <<EOF
# Google Cloud Connection Details
GCP_PROJECT_ID=$GCP_PROJECT_ID
GCP_REGION=$GCP_REGION

# CX Agent Studio Configuration
CES_AGENT_ID=$CES_AGENT_ID

# Developer Details
DEVELOPER_EMAIL=$DEVELOPER_EMAIL

# Voice runner (ces-voice-test): TTS engine
CES_VOICE_TTS=$DEFAULT_TTS

# Optional Lucid integration for .agents/skills/gemini/*
LUCID_API_KEY=$LUCID_API_KEY
LUCID_TOKEN=$LUCID_API_KEY

# Optional Jira integration for design-audit workflows
JIRA_SITE=$JIRA_SITE
JIRA_USER=$JIRA_USER
JIRA_TOKEN=$JIRA_TOKEN
JIRA_PROJECT=$JIRA_PROJECT

# Optional PractiTest integration for test results
PRACTITEST_API_KEY=$PRACTITEST_API_KEY
PRACTITEST_PROJECT_ID=$PRACTITEST_PROJECT_ID
PRACTITEST_FILTER_ID=$PRACTITEST_FILTER_ID
PRACTITEST_EMAIL=$PRACTITEST_EMAIL
EOF

echo ""
echo "✅ Configuration successfully written to $ENV_FILE"
echo "============================================================"
echo ""

# --- Verify gcloud CLI and project access ---
echo "Checking local Google Cloud SDK prerequisites..."
echo ""

load_env
if ! verify_core_config; then
  echo ""
  echo "============================================================"
  echo "Setup blocked. Fix the errors above, then run:"
  echo "  ./setup.sh --verify"
  echo "============================================================"
  exit 1
fi

echo ""
echo "============================================================"
echo "Setup verified. Next steps:"
echo "1. Open CX Agent Studio for project $GCP_PROJECT_ID."
echo "2. Deploy callbacks from templates/callbacks.py or paste them into the console."
echo "3. Customize templates/openapi_tool_template.json for each backend API."
echo "4. Add optional Lucid/Jira tokens to .env before running related .agents skills."
echo "============================================================"
echo ""
