#!/usr/bin/env bash
# Robo-Burnie Raspberry Pi setup script.
# Runs as the user who invokes the script (repo, poetry, and crontab are for that user).
# Safe to run multiple times (idempotent). Copy to the Pi or run from a clone.
#
# Usage:
#   From repo root:  ./setup-pi.sh
#   From elsewhere:  bash setup-pi.sh   (script will clone repo to ~/code/Robo-Burnie and re-run from there)

set -e

REPO_URL="${REPO_URL:-https://github.com/adelprete/Robo-Burnie.git}"
CODE_DIR="${HOME}/code"
REPO_DIR="${CODE_DIR}/Robo-Burnie"

# --- Helpers ---
in_repo() {
  [[ -f crontab.example && -f pyproject.toml ]]
}

ensure_path() {
  export PATH="${HOME}/.local/bin:${PATH}"
}

# --- System setup (idempotent) ---
run_system_setup() {
  echo "==> System: apt update and install vim, pipx..."
  sudo apt-get update -qq
  sudo apt-get install -y vim pipx
  echo "==> System: pipx install poetry and ensurepath..."
  pipx install poetry
  pipx ensurepath
  ensure_path
}

# --- Repo: clone or pull, then re-exec from repo if we're not in it ---
ensure_repo_and_cd() {
  if in_repo; then
    return 0
  fi

  run_system_setup
  mkdir -p "$CODE_DIR"

  if [[ ! -d "$REPO_DIR" ]]; then
    echo "==> Cloning repo to $REPO_DIR..."
    git clone "$REPO_URL" "$REPO_DIR"
  else
    echo "==> Repo exists, pulling latest..."
    (cd "$REPO_DIR" && git pull) || true
  fi

  echo "==> Re-running setup from repo..."
  exec bash "$REPO_DIR/setup-pi.sh"
}

# --- Project setup (poetry, logs, crontab) ---
run_project_setup() {
  ensure_path

  echo "==> Poetry: config and install..."
  poetry config keyring.enabled false
  poetry install

  echo "==> Creating logs directory..."
  mkdir -p logs

  echo "==> Installing crontab..."
  PROJECT_DIR="$(pwd)"
  VENV="$(poetry env info -p)"
  sed "s|^PROJECT_DIR=.*|PROJECT_DIR=${PROJECT_DIR}|;s|^VENV=.*|VENV=${VENV}|" crontab.example | crontab -

  echo ""
  echo "Setup complete. Crontab installed for $(whoami). Logs: $PROJECT_DIR/logs/"
}

# --- Main ---
main() {
  # If we're not in the repo, do system setup, clone/pull, and re-exec from repo.
  ensure_repo_and_cd

  # We're in the repo (possibly after re-exec). Run system setup (idempotent) then project setup.
  run_system_setup
  run_project_setup
}

main "$@"
