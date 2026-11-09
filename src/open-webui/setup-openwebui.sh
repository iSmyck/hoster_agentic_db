#!/usr/bin/env bash
set -euo pipefail

# Idempotent setup script for the pinned Open WebUI upstream checkout.
# Clones https://github.com/open-webui/open-webui.git and checks out the
# T00 baseline commit if upstream/ is missing or not at that commit.

REPO_URL="https://github.com/open-webui/open-webui.git"
PINNED_COMMIT="c38885a1a737da4968f157092f304f3b5481d0bf"
PINNED_TAG="v0.13.0"
UPSTREAM_DIR="upstream"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() {
    echo "[setup-openwebui] $*"
}

is_at_pinned_commit() {
    local head
    head="$(git -C "$UPSTREAM_DIR" rev-parse HEAD 2>/dev/null || true)"
    [[ "$head" == "$PINNED_COMMIT" ]]
}

if [[ -d "$UPSTREAM_DIR/.git" ]]; then
    log "Found existing upstream checkout."
    if is_at_pinned_commit; then
        log "Upstream is already at pinned commit $PINNED_COMMIT."
        exit 0
    fi

    log "Fetching latest refs..."
    git -C "$UPSTREAM_DIR" fetch --no-tags origin "$PINNED_TAG"

    log "Checking out pinned commit $PINNED_COMMIT..."
    git -C "$UPSTREAM_DIR" -c advice.detachedHead=false checkout "$PINNED_COMMIT"

    if is_at_pinned_commit; then
        log "Success: upstream now at $PINNED_COMMIT."
        exit 0
    else
        log "ERROR: checkout did not land on expected commit." >&2
        exit 1
    fi
fi

if [[ -e "$UPSTREAM_DIR" ]]; then
    log "ERROR: '$UPSTREAM_DIR' exists but is not a git repository. Remove it manually and re-run." >&2
    exit 1
fi

log "Cloning Open WebUI $PINNED_TAG ($PINNED_COMMIT)..."
git clone --no-checkout --filter=blob:none "$REPO_URL" "$UPSTREAM_DIR"

git -C "$UPSTREAM_DIR" fetch --no-tags origin "$PINNED_TAG"
git -C "$UPSTREAM_DIR" -c advice.detachedHead=false checkout "$PINNED_COMMIT"

if is_at_pinned_commit; then
    log "Success: cloned and checked out $PINNED_COMMIT."
else
    log "ERROR: cloned checkout is not at expected commit." >&2
    exit 1
fi
