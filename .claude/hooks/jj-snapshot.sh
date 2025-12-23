#!/usr/bin/env bash
# Claude Code hook to create jujutsu snapshots after file modifications
# Runs `jj status` which triggers an automatic working copy snapshot

set -euo pipefail

# Check if we're in a jj repository
if ! jj root &>/dev/null; then
    exit 0
fi

# Run jj status to trigger a snapshot and show changes
# The --quiet flag suppresses output for cleaner Claude Code experience
jj status --quiet

exit 0
